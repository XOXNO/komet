from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KVariable
from pyk.kast.outer import KClaim, KFlatModule
from pyk.kast.prelude.ml import mlAnd, mlCeil, mlEqualsTrue
from pyk.kcfg import KCFG
from pyk.kcfg.kcfg import Vacuous
from pyk.kore.rpc import SatResult, UnknownResult, UnsatResult
from pyk.proof import APRProof, ProofStatus

from komet import proof as proof_module
from komet.utils import KSorobanError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


@pytest.mark.parametrize(
    'change', ['claim', 'extra_module', 'haskell', 'llvm', 'llvm_library', 'runner', 'missing_manifest']
)
def test_resume_checks_actual_inputs(tmp_path: Path, monkeypatch: MonkeyPatch, change: str) -> None:
    for name in ['haskell', 'llvm']:
        definition = tmp_path / name
        definition.mkdir()
        (definition / 'definition.kore').write_text(name)
    (tmp_path / 'llvm' / 'interpreter.so').write_bytes(b'compiled hooks')
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(path=tmp_path / 'haskell'))
    monkeypatch.setattr(proof_module, 'library_definition', lambda: SimpleNamespace(path=tmp_path / 'llvm'))
    proof_dir = tmp_path / 'proofs'
    claim = KClaim(KVariable('ORIGINAL'))
    proof_module._check_proof_inputs('claim', claim, None, proof_dir)
    saved = proof_dir / 'claim' / 'proof.json'
    saved.write_text('{"status": "passed"}')
    proof_module._check_proof_inputs('claim', claim, None, proof_dir)

    extra = None
    if change == 'claim':
        claim = KClaim(KVariable('DIFFERENT'))
    elif change == 'extra_module':
        extra = KFlatModule('ADDITIONAL-LEMMAS', [])
    elif change == 'missing_manifest':
        (saved.parent / 'inputs.json').unlink()
    elif change == 'llvm_library':
        (tmp_path / 'llvm' / 'interpreter.so').write_bytes(b'changed native hooks')
    elif change == 'runner':
        runner = tmp_path / 'proof.py'
        runner.write_text('changed proof engine')
        monkeypatch.setattr(proof_module, '__file__', str(runner))
    else:
        (tmp_path / change / 'definition.kore').write_text('different semantics')
    with pytest.raises(ValueError, match='fresh proof directory'):
        proof_module._check_proof_inputs('claim', claim, extra, proof_dir)
    assert saved.read_text() == '{"status": "passed"}'


@pytest.mark.parametrize('error', [RuntimeError('RPC disconnected'), KeyboardInterrupt()])
def test_execution_failure_preserves_checkpoint(monkeypatch: MonkeyPatch, error: BaseException) -> None:
    proof = Mock()
    prover = Mock()
    prover.advance_proof.side_effect = error
    monkeypatch.setattr(proof_module, '_check_proof_inputs', lambda *args: None)
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(kdefinition=None))
    monkeypatch.setattr(proof_module.APRProof, 'from_claim', lambda *args, **kwargs: proof)
    monkeypatch.setattr(proof_module, '_constraints_unsat', lambda *args: False)
    proof.kcfg.is_vacuous.return_value = False
    proof.kcfg.node.return_value.cterm.is_bottom = False
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(Mock()))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: prover)
    with pytest.raises(type(error)):
        proof_module.run_claim('claim', KClaim(KVariable('CLAIM')))
    proof.write_proof_data.assert_called_once_with()


@pytest.mark.parametrize('result', [SatResult(None), UnknownResult(), UnsatResult()])
def test_custom_step_requires_explicit_unsat(result: object) -> None:
    original = mlEqualsTrue(KVariable('P', 'Bool'))
    state = CTerm(KApply('<generatedTop>'), [original])
    # Model normalization adding a definedness predicate; it must reach the SMT query intact.
    normalized = mlAnd([original, mlCeil(KVariable('PARTIAL', 'Int'))])
    cs = Mock()
    cs.kast_simplify.return_value = normalized, ()
    cs._kore_client.get_model.return_value = result
    step = proof_module.SorobanSemantics().custom_step(state, cs, 7)
    assert isinstance(step, Vacuous) == isinstance(result, UnsatResult)
    cs.kast_simplify.assert_called_once_with(mlAnd(state.constraints), module_name=None)
    cs.kast_to_kore.assert_called_once_with(normalized)
    cs._kore_client.get_model.assert_called_once_with(cs.kast_to_kore.return_value, module_name=None)
    assert state.constraints == (original,)
    cs.get_model.assert_not_called()


@pytest.mark.parametrize('stage', ['kast_simplify', 'get_model'])
def test_custom_step_propagates_backend_errors(stage: str) -> None:
    state = CTerm(KApply('<generatedTop>'), [mlEqualsTrue(KVariable('P', 'Bool'))])
    cs = Mock()
    cs.kast_simplify.return_value = state.constraints[0], ()
    getattr(cs if stage == 'kast_simplify' else cs._kore_client, stage).side_effect = RuntimeError('backend failed')
    with pytest.raises(RuntimeError, match='backend failed'):
        proof_module.SorobanSemantics().custom_step(state, cs, 7)


def test_custom_step_skips_unconstrained_state_but_checks_bottom() -> None:
    cs = Mock()
    assert proof_module.SorobanSemantics().custom_step(CTerm(KApply('<generatedTop>')), cs, 1) is None
    cs.kast_simplify.assert_not_called()
    bottom = CTerm.bottom()
    cs.kast_simplify.return_value = bottom.kast, ()
    cs._kore_client.get_model.return_value = UnsatResult()
    assert isinstance(proof_module.SorobanSemantics().custom_step(bottom, cs, 1), Vacuous)
    cs.kast_simplify.assert_called_once_with(bottom.kast, module_name=None)


@pytest.mark.parametrize('resumed', [False, True])
@pytest.mark.parametrize('result', [SatResult(None), UnknownResult(), UnsatResult()])
def test_initial_feasibility_before_subsumption_or_resume(
    tmp_path: Path, monkeypatch: MonkeyPatch, resumed: bool, result: object
) -> None:
    graph = KCFG()
    state = CTerm(KApply('<generatedTop>'), [mlEqualsTrue(KVariable('P', 'Bool'))])
    initial = graph.create_node(state)
    target = graph.create_node(CTerm(KApply('<generatedTop>')))
    graph.create_cover(initial.id, target.id)
    proof = APRProof('claim', graph, [], initial.id, target.id, {})
    assert proof.status == ProofStatus.PASSED
    proof.write_proof_data = Mock()
    cs = Mock()
    cs.kast_simplify.return_value = mlAnd(state.constraints), ()
    cs._kore_client.get_model.return_value = result
    prover = Mock()
    monkeypatch.setattr(proof_module, '_check_proof_inputs', lambda *args: None)
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(kdefinition=None))
    monkeypatch.setattr(proof_module.APRProof, 'proof_data_exists', lambda *args: resumed)
    monkeypatch.setattr(proof_module.APRProof, 'read_proof_data', lambda *args: proof)
    monkeypatch.setattr(proof_module.APRProof, 'from_claim', lambda *args, **kwargs: proof)
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(SimpleNamespace(cterm_symbolic=cs)))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: prover)
    if isinstance(result, UnsatResult):
        with pytest.raises(KSorobanError, match='Vacuous initial state'):
            proof_module.run_claim('claim', KClaim(KVariable('CLAIM')), proof_dir=tmp_path)
        prover.advance_proof.assert_not_called()
    else:
        assert proof_module.run_claim('claim', KClaim(KVariable('CLAIM')), proof_dir=tmp_path) is proof
        prover.advance_proof.assert_called_once_with(proof)
    cs._kore_client.get_model.assert_called_once()
    proof.write_proof_data.assert_called_once_with()


@pytest.mark.parametrize('already_vacuous', [False, True])
def test_initial_vacuity_mark_is_rejected(monkeypatch: MonkeyPatch, already_vacuous: bool) -> None:
    proof = Mock()
    proof.kcfg.is_vacuous.side_effect = [True] if already_vacuous else [False, True]
    proof.kcfg.node.return_value.cterm.is_bottom = False
    prover = Mock()
    monkeypatch.setattr(proof_module, '_check_proof_inputs', lambda *args: None)
    monkeypatch.setattr(proof_module, '_constraints_unsat', lambda *args: False)
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(kdefinition=None))
    monkeypatch.setattr(proof_module.APRProof, 'from_claim', lambda *args, **kwargs: proof)
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(Mock()))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: prover)
    with pytest.raises(KSorobanError, match='Vacuous initial state'):
        proof_module.run_claim('claim', KClaim(KVariable('CLAIM')))
    assert prover.advance_proof.call_count == (0 if already_vacuous else 1)
    proof.write_proof_data.assert_called_once_with()


@pytest.mark.parametrize('resumed', [False, True])
def test_initial_bottom_rejected_even_if_smt_unknown(tmp_path: Path, monkeypatch: MonkeyPatch, resumed: bool) -> None:
    proof = Mock()
    proof.kcfg.node.return_value.cterm = CTerm.bottom()
    proof.kcfg.is_vacuous.return_value = False
    cs = Mock()
    cs._kore_client.get_model.return_value = UnknownResult()
    prover = Mock()
    monkeypatch.setattr(proof_module, '_check_proof_inputs', lambda *args: None)
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(kdefinition=None))
    monkeypatch.setattr(proof_module.APRProof, 'proof_data_exists', lambda *args: resumed)
    monkeypatch.setattr(proof_module.APRProof, 'read_proof_data', lambda *args: proof)
    monkeypatch.setattr(proof_module.APRProof, 'from_claim', lambda *args, **kwargs: proof)
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(SimpleNamespace(cterm_symbolic=cs)))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: prover)
    with pytest.raises(KSorobanError, match='Vacuous initial state'):
        proof_module.run_claim('claim', KClaim(KVariable('CLAIM')), proof_dir=tmp_path)
    prover.advance_proof.assert_not_called()
    cs._kore_client.get_model.assert_not_called()
    proof.write_proof_data.assert_called_once_with()


def test_extra_module_used_by_preflight_and_hook(monkeypatch: MonkeyPatch) -> None:
    proof = Mock()
    state = CTerm(KApply('<generatedTop>'), [mlEqualsTrue(KVariable('P', 'Bool'))])
    proof.kcfg.node.return_value.cterm = state
    proof.kcfg.is_vacuous.return_value = False
    cs = Mock()
    cs.add_module.return_value = 'EXTRA'
    cs.kast_simplify.return_value = mlAnd(state.constraints), ()
    cs._kore_client.get_model.return_value = SatResult(None)
    explore = SimpleNamespace(cterm_symbolic=cs)
    extra = KFlatModule('EXTRA', [])
    monkeypatch.setattr(proof_module, '_check_proof_inputs', lambda *args: None)
    monkeypatch.setattr(proof_module, 'symbolic_definition', lambda: SimpleNamespace(kdefinition=None))
    monkeypatch.setattr(proof_module.APRProof, 'from_claim', lambda *args, **kwargs: proof)
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(explore))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: Mock())
    proof_module.run_claim('claim', KClaim(KVariable('CLAIM')), extra_module=extra)
    cs.add_module.assert_called_once_with(extra, name_as_id=True)
    assert explore.kcfg_semantics.custom_step(state, cs, 3) is None
    assert cs.kast_simplify.call_count == cs._kore_client.get_model.call_count == 2
    for call in cs.kast_simplify.call_args_list + cs._kore_client.get_model.call_args_list:
        assert call.kwargs['module_name'] == 'EXTRA'
