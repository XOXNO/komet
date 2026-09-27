from __future__ import annotations

import json
from contextlib import contextmanager
from hashlib import sha256
from typing import TYPE_CHECKING

from pyk.cterm import cterm_symbolic
from pyk.kast.outer import KApply, KRewrite
from pyk.kcfg import KCFGExplore
from pyk.kcfg.semantics import DefaultSemantics
from pyk.konvert import kast_to_kore, kore_to_kast
from pyk.proof import APRProof, APRProver
from pyk.proof.implies import EqualityProof, ImpliesProver

from .native_stack import booster_command
from .utils import library_definition, symbolic_definition

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pyk.kast.inner import KInner
    from pyk.kast.outer import KClaim, KFlatModule
    from pyk.utils import BugReport


@contextmanager
def _explore_context(id: str, bug_report: BugReport | None) -> Iterator[KCFGExplore]:
    with cterm_symbolic(
        definition=symbolic_definition().kdefinition,
        definition_dir=symbolic_definition().path,
        llvm_definition_dir=library_definition().path,
        kore_rpc_command=booster_command(),
        id=id if bug_report else None,
        bug_report=bug_report,
    ) as cts:
        yield KCFGExplore(cts)


class SorobanSemantics(DefaultSemantics): ...


def _check_proof_inputs(id: str, claim: KClaim, extra_module: KFlatModule | None, proof_dir: Path | None) -> None:
    if proof_dir is None:
        return

    llvm = library_definition()
    libraries = {
        name: sha256((llvm.path / name).read_bytes()).hexdigest()
        for name in ['interpreter.so', 'interpreter.dylib']
        if (llvm.path / name).is_file()
    }
    if not libraries:
        raise ValueError(f'Compiled LLVM library missing in {llvm.path}')
    inputs = {
        'claim': sha256(json.dumps(claim.to_dict(), sort_keys=True).encode()).hexdigest(),
        'extra_module': None if extra_module is None else extra_module.to_dict(),
        'definitions': {
            name: sha256((definition.path / 'definition.kore').read_bytes()).hexdigest()
            for name, definition in [('haskell', symbolic_definition()), ('llvm', llvm)]
        },
        'llvm_libraries': libraries,
    }
    manifest = proof_dir / id / 'inputs.json'
    if APRProof.proof_data_exists(id, proof_dir):
        if not manifest.is_file() or json.loads(manifest.read_text()) != inputs:
            raise ValueError(f'Proof inputs changed or are unrecorded for {id}; use a fresh proof directory.')
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(inputs, sort_keys=True, indent=2) + '\n')


def run_claim(
    id: str,
    claim: KClaim,
    extra_module: KFlatModule | None = None,
    proof_dir: Path | None = None,
    bug_report: BugReport | None = None,
) -> APRProof:
    _check_proof_inputs(id, claim, extra_module, proof_dir)
    if proof_dir is not None and APRProof.proof_data_exists(id, proof_dir):
        proof = APRProof.read_proof_data(proof_dir, id)
    else:
        proof = APRProof.from_claim(symbolic_definition().kdefinition, claim=claim, logs={}, proof_dir=proof_dir)

    try:
        with _explore_context(id, bug_report) as kcfg_explore:
            prover = APRProver(kcfg_explore, extra_module=extra_module)
            prover.advance_proof(proof)
    finally:
        proof.write_proof_data()
    return proof


def is_functional(claim: KClaim) -> bool:
    claim_lhs = claim.body
    if type(claim_lhs) is KRewrite:
        claim_lhs = claim_lhs.lhs
    return not (type(claim_lhs) is KApply and claim_lhs.label.name == '<generatedTop>')


def run_functional_claim(
    claim: KClaim, proof_dir: Path | None = None, bug_report: BugReport | None = None
) -> EqualityProof:
    _check_proof_inputs(claim.label, claim, None, proof_dir)
    if proof_dir is not None and EqualityProof.proof_data_exists(claim.label, proof_dir):
        proof = EqualityProof.read_proof_data(proof_dir, claim.label)
    else:
        proof = EqualityProof.from_claim(claim, symbolic_definition().kdefinition, proof_dir=proof_dir)

    try:
        with _explore_context(claim.label, bug_report) as kcfg_explore:
            prover = ImpliesProver(proof, kcfg_explore=kcfg_explore)
            prover.advance_proof(proof)
    finally:
        proof.write_proof_data()
    return proof


def simplify(kast: KInner, bug_report: BugReport | None = None) -> KInner:
    pat = kast_to_kore(symbolic_definition().kdefinition, kast)
    with _explore_context('', bug_report=bug_report) as kcfg_explore:
        simplified = kcfg_explore.cterm_symbolic._kore_client.simplify(pat)[0]
        return kore_to_kast(symbolic_definition().kdefinition, simplified)
