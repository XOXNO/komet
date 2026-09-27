from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from pyk.kast.inner import KVariable
from pyk.kast.outer import KClaim, KFlatModule

from komet import proof as proof_module

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


@pytest.mark.parametrize('change', ['claim', 'extra_module', 'haskell', 'llvm', 'llvm_library', 'missing_manifest'])
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
    monkeypatch.setattr(proof_module, '_explore_context', lambda *args: nullcontext(None))
    monkeypatch.setattr(proof_module, 'APRProver', lambda *args, **kwargs: prover)
    with pytest.raises(type(error)):
        proof_module.run_claim('claim', KClaim(KVariable('CLAIM')))
    proof.write_proof_data.assert_called_once_with()
