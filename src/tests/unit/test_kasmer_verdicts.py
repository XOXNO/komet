from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from pyk.cterm import CTerm
from pyk.kast.att import Atts, KAtt
from pyk.kast.inner import KApply, KSequence, KVariable
from pyk.kast.outer import KClaim, KFlatModule
from pyk.kast.prelude.ml import mlEqualsTrue
from pyk.kast.prelude.utils import token
from pyk.kore.rpc import UnsatResult
from pyk.kore.syntax import SortApp, Top
from pyk.proof import ProofStatus

from komet import kasmer as kasmer_module
from komet import komet as cli_module
from komet import proof as proof_module
from komet.kasmer import ContractBinding, FuzzError, Kasmer, _run_test_case
from komet.kast.syntax import STEPS_TERMINATOR, sc_bool
from komet.utils import KSorobanError

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def _test_terminal(exit_code: int, pending: bool = False, mismatch: bool = False) -> KApply:
    k = KSequence(KApply('pending')) if pending else KSequence()
    stack = KApply('.List{"hostStackList"}')
    if mismatch:
        k = KSequence(KApply('expectResult', sc_bool(True)), KApply('#resetHost'))
        stack = KApply('hostStackList', sc_bool(False), stack)
    return KApply(
        '<generatedTop>',
        KApply('<exitCode>', token(exit_code)),
        KApply('<program>', STEPS_TERMINATOR),
        KApply('<k>', k),
        KApply('<instrs>', KSequence()),
        KApply('<hostStack>', stack),
        KApply('<valstack>', KApply('.ValStack')),
        KApply('<callStack>', KApply('.List')),
    )


@pytest.mark.parametrize('exit_code, expected', [(0, True), (1, False)])
def test_fuzz_uses_krun_and_checks_terminal_verdict(monkeypatch: MonkeyPatch, exit_code: int, expected: bool) -> None:
    pattern = Top(SortApp('SortGeneratedTopCell'))
    definition = Mock()
    definition.krun.run_process.return_value = CompletedProcess([], exit_code, pattern.text, '')
    monkeypatch.setattr(kasmer_module, 'kore_to_kast', lambda *args: _test_terminal(exit_code, mismatch=exit_code == 1))
    assert _run_test_case(definition, pattern) is expected
    definition.krun.run_process.assert_called_once_with(pattern, term=True)


@pytest.mark.parametrize('returncode, stdout', [(-6, ''), (1, ''), (0, 'not kore')])
def test_fuzz_backend_errors_are_infrastructure_failures(returncode: int, stdout: str) -> None:
    definition = Mock()
    definition.krun.run_process.return_value = CompletedProcess(
        [], returncode, stdout, 'Called finish_rewriting with no output file specified'
    )
    with pytest.raises(RuntimeError, match='Komet backend'):
        _run_test_case(definition, Top(SortApp('SortGeneratedTopCell')))


@pytest.mark.parametrize('terminal', [_test_terminal(0, pending=True), _test_terminal(1), KApply('<generatedTop>')])
def test_fuzz_rejects_incomplete_or_inconsistent_terminals(monkeypatch: MonkeyPatch, terminal: KApply) -> None:
    pattern = Top(SortApp('SortGeneratedTopCell'))
    definition = Mock()
    definition.krun.run_process.return_value = CompletedProcess([], 0, pattern.text, '')
    monkeypatch.setattr(kasmer_module, 'kore_to_kast', lambda *args: terminal)
    with pytest.raises(RuntimeError, match='Komet backend'):
        _run_test_case(definition, pattern)


@pytest.mark.parametrize('pending', [False, True])
def test_fuzz_does_not_call_unknown_stuck_execution_a_counterexample(monkeypatch: MonkeyPatch, pending: bool) -> None:
    pattern = Top(SortApp('SortGeneratedTopCell'))
    definition = Mock()
    definition.krun.run_process.return_value = CompletedProcess([], 1, pattern.text, '')
    monkeypatch.setattr(kasmer_module, 'kore_to_kast', lambda *args: _test_terminal(1, pending=pending))
    with pytest.raises(RuntimeError, match='without a confirmed Boolean result mismatch'):
        _run_test_case(definition, pattern)


@pytest.mark.parametrize('outcome', ['pass', 'false', 'abort'])
def test_fuzz_loop_reports_only_property_failures(monkeypatch: MonkeyPatch, outcome: str) -> None:
    pattern = Top(SortApp('SortGeneratedTopCell'))
    monkeypatch.setattr(kasmer_module, 'kast_to_kore', lambda *args: pattern)
    monkeypatch.setattr(kasmer_module, 'subst_on_program_cell', lambda *args: pattern)
    execute = Mock(return_value=outcome == 'pass')
    if outcome == 'abort':
        execute.side_effect = RuntimeError('Komet backend execution failed (exit -6)')
    monkeypatch.setattr(kasmer_module, '_run_test_case', execute)
    binding = ContractBinding('test_witness', (), ())
    task = Mock(binding=binding)
    kasmer = Kasmer(Mock())
    if outcome == 'pass':
        kasmer.run_test(KVariable('PROGRAM_CELL'), {}, binding, 1, task)
    else:
        with pytest.raises(FuzzError if outcome == 'false' else RuntimeError):
            kasmer.run_test(KVariable('PROGRAM_CELL'), {}, binding, 1, task)
    if outcome == 'false':
        task.fail.assert_called_once_with()
    else:
        task.fail.assert_not_called()
    execute.assert_called()


@pytest.mark.parametrize('functional', [False, True])
@pytest.mark.parametrize('status', list(ProofStatus))
def test_raw_proof_requires_passed(monkeypatch: MonkeyPatch, functional: bool, status: ProofStatus) -> None:
    claim = KClaim(KVariable('VALUE') if functional else KApply('<generatedTop>'), att=KAtt([Atts.LABEL('claim')]))
    definition = Mock()
    definition.kprove.parse_modules.return_value = SimpleNamespace(modules=[KFlatModule('CLAIMS', [claim])])
    proof = SimpleNamespace(status=status, summary='proof summary')
    runner = Mock(return_value=proof)
    monkeypatch.setattr(kasmer_module, 'run_functional_claim' if functional else 'run_claim', runner)
    kasmer = Kasmer(definition)
    if status == ProofStatus.PASSED:
        kasmer.prove_raw(Path('claim.k'))
    else:
        with pytest.raises(KSorobanError) as error:
            kasmer.prove_raw(Path('claim.k'))
        assert error.value.args[0] == (proof if functional else proof.summary)
    runner.assert_called_once()


@pytest.mark.parametrize('label', [None, 'missing'])
def test_raw_proof_rejects_empty_selection(label: str | None) -> None:
    claim = KClaim(KVariable('VALUE'), att=KAtt([Atts.LABEL('present')]))
    definition = Mock()
    definition.kprove.parse_modules.return_value = SimpleNamespace(
        modules=[KFlatModule('CLAIMS', [] if label is None else [claim])]
    )
    with pytest.raises(KSorobanError, match='No matching claims'):
        Kasmer(definition).prove_raw(Path('claim.k'), label=label)


@pytest.mark.parametrize('method', ['deploy_and_run', 'deploy_and_prove'])
@pytest.mark.parametrize('names', [[], ['init', 'main']])
def test_contract_run_rejects_empty_test_discovery(monkeypatch: MonkeyPatch, method: str, names: list[str]) -> None:
    kasmer = Kasmer(Mock())
    monkeypatch.setattr(
        kasmer, 'contract_bindings', lambda _, **kwargs: [ContractBinding(name, (), ()) for name in names]
    )
    monkeypatch.setattr(kasmer, 'kast_from_wasm', lambda _: KVariable('CODE'))
    monkeypatch.setattr(kasmer, 'contract_protocol', lambda _: 28)
    deploy = Mock(return_value=(KVariable('CONF'), {}))
    monkeypatch.setattr(kasmer, 'deploy_test', deploy)
    with pytest.raises(KeyError, match='No test functions'):
        getattr(kasmer, method)(Path('empty.wasm'), ())
    deploy.assert_not_called()


@pytest.mark.parametrize('vacuity', ['unsat', 'bottom', 'marked'])
def test_raw_cli_rejects_vacuous_initial_state(monkeypatch: MonkeyPatch, vacuity: str) -> None:
    claim = KClaim(KApply('<generatedTop>'), att=KAtt([Atts.LABEL('claim')]))
    definition = Mock()
    definition.kprove.parse_modules.return_value = SimpleNamespace(modules=[KFlatModule('CLAIMS', [claim])])
    proof = Mock(status=ProofStatus.PASSED)
    state = CTerm(KApply('<generatedTop>'), [mlEqualsTrue(KVariable('P', 'Bool'))])
    proof.kcfg.node.return_value.cterm = CTerm.bottom() if vacuity == 'bottom' else state
    proof.kcfg.is_vacuous.return_value = vacuity == 'marked'
    cs = Mock()
    cs.kast_simplify.return_value = state.constraints[0], ()
    cs._kore_client.get_model.return_value = UnsatResult()
    prover = Mock()
    monkeypatch.setattr(cli_module, 'emit_event', lambda *args: None)
    monkeypatch.setattr(cli_module, 'symbolic_definition', lambda: definition)
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: definition)
    monkeypatch.setattr(proof_module, '_check_proof_inputs', lambda *args: None)
    monkeypatch.setattr(proof_module.APRProof, 'from_claim', lambda *args, **kwargs: proof)
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(SimpleNamespace(cterm_symbolic=cs)))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: prover)
    with pytest.raises(SystemExit) as error:
        cli_module._exec_prove_raw(claim_file=Path('claim.k'), label=None, extra_module=None, proof_dir=None)
    assert error.value.code == 1
    prover.advance_proof.assert_not_called()
    proof.write_proof_data.assert_called_once_with()
