from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from pyk.cterm import CTerm
from pyk.kast.att import Atts, KAtt
from pyk.kast.inner import KApply, KVariable
from pyk.kast.outer import KClaim, KFlatModule
from pyk.kast.prelude.ml import mlEqualsTrue
from pyk.kore.rpc import UnsatResult
from pyk.proof import ProofStatus

from komet import kasmer as kasmer_module
from komet import komet as cli_module
from komet import proof as proof_module
from komet.kasmer import ContractBinding, Kasmer
from komet.utils import KSorobanError

if TYPE_CHECKING:
    from pytest import MonkeyPatch


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
    monkeypatch.setattr(kasmer, 'contract_bindings', lambda _, **kwargs: [ContractBinding(name, (), ()) for name in names])
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
