import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, KVariable, Subst
from pyk.kast.outer import KFlatModule, KImport
from pyk.kast.prelude.ml import is_bottom, mlCeil, mlEqualsTrue
from pyk.kast.prelude.utils import token
from pyk.kcfg import KCFG, KCFGExplore
from pyk.kcfg.kcfg import Vacuous
from pyk.konvert import kast_to_kore, kore_to_kast
from pyk.proof import APRProof, APRProver

from komet.proof import SorobanSemantics, _explore_context
from komet.utils import symbolic_definition


@pytest.fixture(scope='module')
def signed_explore() -> Iterator[KCFGExplore]:
    with _explore_context('signed-total-regression', None) as explore:
        yield explore


@pytest.fixture(scope='module')
def signed_simplify(signed_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        pattern = kast_to_kore(definition, term)
        result = signed_explore.cterm_symbolic._kore_client.simplify(pattern)[0]
        return kore_to_kast(definition, result)

    return simplify


def _signed(width: int, term: KInner) -> KApply:
    return KApply('#signedTotal', KApply(f'i{width}'), term)


def _contains_signed_total(term: KInner) -> bool:
    return (isinstance(term, KApply) and term.label.name == '#signedTotal') or any(
        _contains_signed_total(child) for child in term.terms
    )


def test_symbolic_word_sign_boundaries(signed_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for width in [32, 64]:
        bound = 1 << width
        half = bound // 2
        masked = KApply('_&Int_', value, token(bound - 1))
        simplified = signed_simplify(_signed(width, masked))
        assert not _contains_signed_total(simplified)
        for concrete, expected in [(0, 0), (half - 1, half - 1), (half, -half), (bound - 1, -1)]:
            assert signed_simplify(Subst({'X': token(concrete)}).apply(simplified)) == token(expected)


def test_signed_total_requires_word_domain(signed_simplify: Callable[[KInner], KInner]) -> None:
    for width in [32, 64]:
        for value in [KVariable('X', 'Int'), token(-1), token(1 << width)]:
            # The total wrapper has no specified cast behavior outside its domain.
            expression = _signed(width, value)
            assert signed_simplify(expression) == expression


def test_signed_total_preserves_partial_operands(signed_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for width in [32, 64]:
        for mask in [0, (1 << width) - 1]:
            quotient = KApply('_/Int_', value, KVariable('D', 'Int'))
            expression = _signed(width, KApply('_&Int_', quotient, token(mask)))
            simplified = signed_simplify(expression)
            undefined = signed_simplify(Subst({'X': token(1), 'D': token(0)}).apply(simplified))
            assert is_bottom(undefined) or is_bottom(signed_simplify(mlCeil(undefined, arg_sort='K')))
            assert signed_simplify(Subst({'X': token(-1), 'D': token(1)}).apply(simplified)) == token(
                0 if mask == 0 else -1
            )


def test_full_masks_use_euclidean_remainders(signed_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for width in [1, 8, 64, 256]:
        bound = 1 << width
        expression = KApply('_&Int_', value, token(bound - 1))
        simplified = signed_simplify(expression)
        assert simplified == KApply('_modInt_', value, token(bound))
        for concrete in [-bound - 1, -bound, -1, 0, bound - 1, bound]:
            assert signed_simplify(Subst({'X': token(concrete)}).apply(simplified)) == token(concrete & (bound - 1))
    for mask in [-1, 5, 6]:
        expression = KApply('_&Int_', value, token(mask))
        assert signed_simplify(expression) == expression
        for concrete in [-9, -1, 0, 7]:
            assert signed_simplify(Subst({'X': token(concrete)}).apply(expression)) == token(concrete & mask)


def test_boolean_word_comparisons(signed_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('B', 'Bool')
    word = KApply('boolToInt', value)
    for number, expected in [(0, KApply('notBool_', value)), (1, value), (2, token(False))]:
        comparison = KApply('_==Int_', word, token(number))
        disagreement = mlEqualsTrue(KApply('_=/=Bool_', comparison, expected))
        assert is_bottom(signed_simplify(disagreement))


def test_boolean_word_preserves_partial_operands(signed_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    expression = KApply('boolToInt', KApply('_==Int_', quotient, token(0)))
    simplified = signed_simplify(expression)
    undefined = signed_simplify(Subst({'X': token(1), 'D': token(0)}).apply(simplified))
    assert is_bottom(undefined) or is_bottom(signed_simplify(mlCeil(undefined, arg_sort='K')))
    for numerator, expected in [(0, 1), (1, 0)]:
        assert signed_simplify(Subst({'X': token(numerator), 'D': token(1)}).apply(simplified)) == token(expected)


@pytest.mark.parametrize('node', [16, 18, 20, 22])
def test_actual_borrow_double_error_paths_are_infeasible(signed_explore: KCFGExplore, node: int) -> None:
    # Exact saved constraints from the branches leading to two MathOverflow terminals.
    # Preserve their full i128 domain and every compiler-generated limb check.
    path = Path(__file__).parent / 'data' / f'borrow_double_node_{node}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    state = CTerm(KApply('<generatedTop>'), constraints)
    step = signed_explore.kcfg_semantics.custom_step(state, signed_explore.cterm_symbolic, node)
    assert isinstance(step, Vacuous)
    assert set(state.constraints) == set(constraints)


@pytest.mark.parametrize('node', [1, 12, 14])
def test_actual_borrow_double_feasible_paths_are_preserved(signed_explore: KCFGExplore, node: int) -> None:
    path = Path(__file__).parent / 'data' / f'borrow_double_node_{node}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    state = CTerm(KApply('<generatedTop>'), constraints)
    assert signed_explore.kcfg_semantics.custom_step(state, signed_explore.cterm_symbolic, node) is None
    assert set(state.constraints) == set(constraints)


def test_extra_module_registration_before_apr_is_idempotent(signed_explore: KCFGExplore) -> None:
    cs = signed_explore.cterm_symbolic
    extra = KFlatModule('PRUNING-EXTRA-SMOKE', [], [KImport(symbolic_definition().kdefinition.main_module_name)])
    module_name = cs.add_module(extra, name_as_id=True)
    semantics = SorobanSemantics(module_name)
    state = CTerm(KApply('<generatedTop>'), [mlEqualsTrue(KApply('_==Int_', KVariable('X', 'Int'), token(1)))])
    assert semantics.custom_step(state, cs, 1) is None
    graph = KCFG()
    initial = graph.create_node(state)
    target = graph.create_node(state)
    proof = APRProof('extra-module-smoke', graph, [], initial.id, target.id, {})
    # Actual APR initialization adds the same named module again and imports it into dependencies.
    APRProver(signed_explore, extra_module=extra).init_proof(proof)
    assert semantics.custom_step(state, cs, 1) is None
