from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from pyk.kast.att import Atts, KAtt
from pyk.kast.inner import KApply, KVariable
from pyk.kast.outer import KClaim, KFlatModule
from pyk.proof import ProofStatus

from komet import kasmer as kasmer_module
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
    monkeypatch.setattr(kasmer, 'contract_bindings', lambda _: [ContractBinding(name, (), ()) for name in names])
    monkeypatch.setattr(kasmer, 'kast_from_wasm', lambda _: KVariable('CODE'))
    monkeypatch.setattr(kasmer, 'contract_protocol', lambda _: 28)
    deploy = Mock(return_value=(KVariable('CONF'), {}))
    monkeypatch.setattr(kasmer, 'deploy_test', deploy)
    with pytest.raises(KeyError, match='No test functions'):
        getattr(kasmer, method)(Path('empty.wasm'), ())
    deploy.assert_not_called()
