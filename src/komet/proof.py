from __future__ import annotations

import json
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from pyk.cterm import cterm_symbolic
from pyk.kast.outer import KApply, KRewrite
from pyk.kast.prelude.ml import mlAnd
from pyk.kcfg import KCFGExplore
from pyk.kcfg.kcfg import Vacuous
from pyk.kcfg.semantics import DefaultSemantics
from pyk.konvert import kast_to_kore, kore_to_kast
from pyk.kore.rpc import SatResult, UnsatResult
from pyk.proof import APRProof, APRProver
from pyk.proof.implies import EqualityProof, ImpliesProver

from .native_stack import booster_command
from .utils import KSorobanError, library_definition, symbolic_definition

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyk.cterm import CTerm, CTermSymbolic
    from pyk.kast.inner import KInner
    from pyk.kast.outer import KClaim, KFlatModule
    from pyk.utils import BugReport


@contextmanager
def _explore_context(id: str, bug_report: BugReport | None) -> Iterator[KCFGExplore]:
    with cterm_symbolic(
        definition=symbolic_definition().kdefinition,
        definition_dir=symbolic_definition().path.resolve(),
        llvm_definition_dir=library_definition().path.resolve(),
        kore_rpc_command=booster_command(),
        smt_timeout=5000,
        id=id if bug_report else None,
        bug_report=bug_report,
    ) as cts:
        yield KCFGExplore(cts, kcfg_semantics=SorobanSemantics())


def _constraints_unsat(
    c: CTerm, cs: CTermSymbolic, module_name: str | None = None, *, sat_fast_path: bool = False
) -> bool:
    if not c.is_bottom and not c.constraints:
        return False
    # Keep the complete normalized predicate, including any definedness conditions.
    predicate = c.config if c.is_bottom else mlAnd(c.constraints)
    # A raw SAT answer only skips optional pruning. Raw UNSAT is insufficient:
    # normalization must preserve the definedness of partial arithmetic.
    if sat_fast_path and isinstance(
        cs._kore_client.get_model(cs.kast_to_kore(predicate), module_name=module_name), SatResult
    ):
        return False
    normalized, _ = cs.kast_simplify(predicate, module_name=module_name)
    # CTermSymbolic.get_model conflates UNSAT and Unknown; only explicit UNSAT closes a path.
    result = cs._kore_client.get_model(cs.kast_to_kore(normalized), module_name=module_name)
    return isinstance(result, UnsatResult)


class SorobanSemantics(DefaultSemantics):
    def __init__(self, module_name: str | None = None):
        self.module_name = module_name

    def custom_step(self, c: CTerm, cs: CTermSymbolic, node_id: int) -> Vacuous | None:
        return Vacuous() if _constraints_unsat(c, cs, self.module_name, sat_fast_path=True) else None


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
    module_inputs = None if extra_module is None else extra_module.to_dict()
    if module_inputs is not None:
        module_inputs['localSentences'].sort(key=lambda sentence: json.dumps(sentence, sort_keys=True))
    inputs = {
        'runner': sha256(Path(__file__).read_bytes()).hexdigest(),
        'claim': sha256(json.dumps(claim.to_dict(), sort_keys=True).encode()).hexdigest(),
        'extra_module': module_inputs,
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
            module_name = None
            if extra_module is not None:
                module_name = kcfg_explore.cterm_symbolic.add_module(extra_module, name_as_id=True)
                kcfg_explore.kcfg_semantics = SorobanSemantics(module_name)
            # APR can subsume the initial node before custom_step, or resume an already passed proof.
            initial = proof.kcfg.node(proof.init).cterm
            if (
                initial.is_bottom
                or proof.kcfg.is_vacuous(proof.init)
                or _constraints_unsat(initial, kcfg_explore.cterm_symbolic, module_name)
            ):
                raise KSorobanError(f'Vacuous initial state for {id}; refusing an empty-domain proof.')
            prover = APRProver(kcfg_explore, execute_depth=1000, fast_check_subsumption=True, extra_module=extra_module)
            prover.advance_proof(proof)
            if proof.kcfg.node(proof.init).cterm.is_bottom or proof.kcfg.is_vacuous(proof.init):
                raise KSorobanError(f'Vacuous initial state for {id}; refusing an empty-domain proof.')
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
