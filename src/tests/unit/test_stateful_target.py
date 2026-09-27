from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from pyk.cterm import CTerm, cterm_build_claim
from pyk.kast.inner import KApply, KSequence, KVariable
from pyk.kast.manip import Subst, extract_lhs, extract_rhs, free_vars, split_config_from
from pyk.kast.prelude.kbool import andBool
from pyk.kast.prelude.ml import mlEqualsTrue
from pyk.kast.prelude.utils import token

from komet import proof as proof_module
from komet.kasmer import ContractBinding, Kasmer
from komet.kast.syntax import STEPS_TERMINATOR, account_id, call_tx, contract_id, sc_bool, set_exit_code, steps_of
from komet.scval import SCBoolType, SCU32Type

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.kast.inner import KInner
    from pyk.kast.outer import KClaim
    from pytest import MonkeyPatch


def _initial_state() -> KApply:
    return KApply(
        '<generatedTop>',
        KApply('<contracts>', KApply('initialContracts')),
        KApply('<accounts>', KApply('initialAccounts')),
        KApply('<contractData>', KApply('initialStorage')),
        KApply('<contractCodes>', KApply('initialCode')),
        KApply('<program>', STEPS_TERMINATOR),
        KApply('<exitCode>', token(0)),
        KApply('<alwaysAllocate>', token(False)),
        KApply('<k>', KSequence()),
        KApply('<instrs>', KSequence()),
        KApply('<hostStack>', KApply('.List{"hostStackList"}')),
        KApply('<valstack>', KApply('.ValStack')),
        KApply('<callStack>', KApply('.List')),
        KApply('<activeContracts>', KApply('.List')),
        KApply('<interimStates>', KApply('.List')),
        KApply('<ledgerTimestamp>', token(0)),
        KApply('<ledgerSequenceNumber>', token(0)),
    )


def _claim(
    monkeypatch: MonkeyPatch, state: KInner | None = None
) -> tuple[KClaim, KInner, dict[str, KInner], ContractBinding]:
    conf, initial = split_config_from(_initial_state() if state is None else state)
    binding = ContractBinding('test_stateful', (SCU32Type(),), (SCBoolType(),))
    runner = Mock()
    monkeypatch.setattr('komet.kasmer.run_claim', runner)
    Kasmer(Mock()).run_prove(conf, initial, binding, always_allocate=True)
    return runner.call_args.args[1], conf, initial, binding


@pytest.mark.parametrize('instances', [1, 2])
def test_world_maps_are_projected_as_whole_cells(monkeypatch: MonkeyPatch, instances: int) -> None:
    state = _initial_state()
    nested = {
        '<contracts>': KApply(
            '<contract>',
            KApply('<contractId>', KApply('initialContractId')),
            KApply('<instanceStorage>', KApply('initialInstanceStorage')),
        ),
        '<accounts>': KApply('<account>', KApply('<balance>', token(50))),
        '<contractCodes>': KApply('<contractCode>', KApply('<codeWasm>', KApply('initialWasm'))),
    }
    if instances == 2:
        for label, map_label in (
            ('<contracts>', '_ContractCellMap_'),
            ('<accounts>', '_AccountCellMap_'),
            ('<contractCodes>', '_ContractCodeCellMap_'),
        ):
            nested[label] = KApply(map_label, nested[label], KApply('secondInstance'))
    state = state.let(
        args=tuple(
            cell.let(args=(nested[cell.label.name],)) if cell.label.name in nested else cell for cell in state.args
        )
    )
    claim, _, initial, _ = _claim(monkeypatch, state)
    world_keys = {'CONTRACTS_CELL', 'ACCOUNTS_CELL', 'CONTRACTCODES_CELL'}
    if instances == 1:
        assert world_keys.isdisjoint(initial)
    else:
        assert world_keys.issubset(initial)
    lhs = extract_lhs(claim.body)
    rhs = extract_rhs(claim.body)
    assert isinstance(lhs, KApply) and isinstance(rhs, KApply)
    for label, contents in nested.items():
        left = next(cell for cell in lhs.args if cell.label.name == label)
        right = next(cell for cell in rhs.args if cell.label.name == label)
        assert left.args == (contents,)
        assert isinstance(right.args[0], KVariable)
        assert right.args[0].name.startswith('?_POST_')
    assert free_vars(rhs) == {
        '?_POST_CONTRACTS_CELL',
        '?_POST_ACCOUNTS_CELL',
        '?_POST_CONTRACTDATA_CELL',
        '?_POST_CONTRACTCODES_CELL',
        '?_ALWAYSALLOCATE_CELL',
    }


def test_target_allows_world_changes_but_preserves_initial_state_and_assertion(monkeypatch: MonkeyPatch) -> None:
    claim, _, initial, binding = _claim(monkeypatch)
    _, lhs = split_config_from(extract_lhs(claim.body))
    _, rhs = split_config_from(extract_rhs(claim.body))
    world_sorts = {
        'CONTRACTS_CELL': 'ContractCellMap',
        'ACCOUNTS_CELL': 'AccountCellMap',
        'CONTRACTDATA_CELL': 'Map',
        'CONTRACTCODES_CELL': 'ContractCodeCellMap',
    }
    for cell, sort in world_sorts.items():
        assert lhs[cell] == initial[cell]
        assert isinstance(rhs[cell], KVariable)
        assert rhs[cell].name == f'?_POST_{cell}'
        assert rhs[cell].sort is not None and rhs[cell].sort.name == sort
    assert len({rhs[cell].name for cell in world_sorts}) == 4
    assert free_vars(extract_rhs(claim.body)) == {rhs[cell].name for cell in world_sorts} | {
        '?_ALWAYSALLOCATE_CELL'
    }
    assert free_vars(extract_lhs(claim.body)).isdisjoint(free_vars(extract_rhs(claim.body)))

    args, constraints = binding.symbolic_args()
    assert claim.requires == andBool(constraints)
    assert lhs['PROGRAM_CELL'] == steps_of(
        [
            set_exit_code(1),
            call_tx(account_id(b'test-account'), contract_id(b'test-contract'), binding.name, args, sc_bool(True)),
            set_exit_code(0),
        ]
    )
    assert lhs['ALWAYSALLOCATE_CELL'] == token(True)
    assert rhs['PROGRAM_CELL'] == STEPS_TERMINATOR
    assert rhs['EXITCODE_CELL'] == token(0)
    for cell in initial.keys() - world_sorts.keys() - {'PROGRAM_CELL', 'EXITCODE_CELL', 'ALWAYSALLOCATE_CELL'}:
        assert lhs[cell] == rhs[cell] == initial[cell]


def test_successful_stateful_terminal_matches_target(monkeypatch: MonkeyPatch) -> None:
    claim, conf, initial, _ = _claim(monkeypatch)
    changed = dict(initial)
    changed.update(
        CONTRACTS_CELL=KApply('updatedContracts'),
        ACCOUNTS_CELL=KApply('updatedAccounts'),
        CONTRACTDATA_CELL=KApply('updatedStorage'),
        CONTRACTCODES_CELL=KApply('updatedCode'),
    )
    target = extract_rhs(claim.body)
    match = target.match(Subst(changed).apply(conf))
    assert match is not None
    assert match['?_POST_CONTRACTDATA_CELL'] == changed['CONTRACTDATA_CELL']


@pytest.mark.parametrize(
    'cell',
    [
        'PROGRAM_CELL',
        'EXITCODE_CELL',
        'K_CELL',
        'INSTRS_CELL',
        'HOSTSTACK_CELL',
        'VALSTACK_CELL',
        'CALLSTACK_CELL',
        'ACTIVECONTRACTS_CELL',
        'INTERIMSTATES_CELL',
        'LEDGERTIMESTAMP_CELL',
        'LEDGERSEQUENCENUMBER_CELL',
    ],
)
def test_world_projection_does_not_ignore_execution_or_ledger_cells(monkeypatch: MonkeyPatch, cell: str) -> None:
    claim, conf, initial, _ = _claim(monkeypatch)
    invalid = dict(initial)
    invalid[cell] = KApply('unexpected')
    assert extract_rhs(claim.body).match(Subst(invalid).apply(conf)) is None


def test_false_assertion_terminal_cannot_match_target(monkeypatch: MonkeyPatch) -> None:
    claim, conf, initial, _ = _claim(monkeypatch)
    failed = dict(initial)
    failed['CONTRACTDATA_CELL'] = KApply('updatedStorage')
    failed['EXITCODE_CELL'] = token(1)
    failed['K_CELL'] = KSequence(KApply('expectResult', sc_bool(True)), KApply('#resetHost'))
    failed['HOSTSTACK_CELL'] = KApply('hostStackList', sc_bool(False), KApply('.List{"hostStackList"}'))
    assert extract_rhs(claim.body).match(Subst(failed).apply(conf)) is None


def test_old_unchanged_world_target_cannot_resume_as_stateful_target(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    claim, conf, initial, binding = _claim(monkeypatch)
    old_rhs = dict(initial)
    del old_rhs['ALWAYSALLOCATE_CELL']
    old_claim, _ = cterm_build_claim(
        binding.name,
        CTerm(extract_lhs(claim.body), [mlEqualsTrue(claim.requires)]),
        CTerm(Subst(old_rhs).apply(conf)),
    )
    assert old_claim != claim
    for name in ['haskell', 'llvm']:
        path = tmp_path / name
        path.mkdir()
        (path / 'definition.kore').write_text(name)
    (tmp_path / 'llvm' / 'interpreter.so').write_bytes(b'unchanged hooks')
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(path=tmp_path / 'haskell'))
    monkeypatch.setattr(proof_module, 'library_definition', lambda: SimpleNamespace(path=tmp_path / 'llvm'))
    proof_dir = tmp_path / 'proofs'
    proof_module._check_proof_inputs(binding.name, old_claim, None, proof_dir)
    saved = proof_dir / binding.name / 'proof.json'
    saved.write_text('{"status":"passed"}')
    proof_module._check_proof_inputs(binding.name, old_claim, None, proof_dir)
    with pytest.raises(ValueError, match='fresh proof directory'):
        proof_module._check_proof_inputs(binding.name, claim, None, proof_dir)
    assert saved.read_text() == '{"status":"passed"}'
