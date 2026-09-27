import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, KVariable, Subst
from pyk.kast.prelude.ml import is_bottom, is_top, mlAnd, mlCeil, mlEqualsTrue
from pyk.kast.prelude.utils import token
from pyk.kcfg import KCFGExplore
from pyk.kcfg.kcfg import Vacuous
from pyk.konvert import kast_to_kore, kore_to_kast
from pyk.kore.rpc import SatResult, UnsatResult

from komet.proof import _explore_context
from komet.utils import symbolic_definition

MIN_WIDTH = '#minWidth(_)_WASM-NUMERIC_Int_Int'


@pytest.fixture(scope='module')
def reverse_explore() -> Iterator[KCFGExplore]:
    with _explore_context('reverse-clz-regression', None) as explore:
        yield explore


@pytest.fixture(scope='module')
def reverse_simplify(reverse_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        pattern = kast_to_kore(definition, term)
        result = reverse_explore.cterm_symbolic._kore_client.simplify(pattern)[0]
        return kore_to_kast(definition, result)

    return simplify


def _has_label(term: KInner, label: str) -> bool:
    return (isinstance(term, KApply) and term.label.name == label) or any(
        _has_label(child, label) for child in term.terms
    )


def _comparison(value: KInner, bound: int, offset: int = 5, modulus: int = 17) -> KInner:
    residue = KApply('_modInt_', KApply('_-Int_', token(offset), KApply(MIN_WIDTH, value)), token(modulus))
    return KApply('_>Int_', residue, token(bound))


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort='K')))


def test_reverse_min_width_all_arms_and_idempotence(
    reverse_simplify: Callable[[KInner], KInner], reverse_explore: KCFGExplore
) -> None:
    value = KVariable('X', 'Int')
    for offset, modulus in [(0, 1), (0, 17), (5, 17), (-12, 17)]:
        width = offset % modulus
        bounded = KApply('_modInt_', value, token(1 << width))
        for bound in [-1, 0, 2, width, width + 1]:
            result = reverse_simplify(_comparison(bounded, bound, offset, modulus))
            assert not _has_label(result, MIN_WIDTH)
            assert reverse_simplify(result) == result
            if bound < 0:
                expected = token(True)
            elif bound >= width:
                expected = token(False)
            else:
                expected = KApply('_<Int_', bounded, token(1 << (width - bound - 1)))
            disagreement = mlEqualsTrue(KApply('_=/=Bool_', result, expected))
            cs = reverse_explore.cterm_symbolic
            normalized, _ = cs.kast_simplify(disagreement)
            assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), UnsatResult)
            for concrete in [0, 1, (1 << width) - 1, -1]:
                n = concrete % (1 << width)
                assert reverse_simplify(Subst({'X': token(concrete)}).apply(result)) == token(
                    ((offset - n.bit_length()) % modulus) > bound
                )


def test_reverse_min_width_keeps_outside_domain(reverse_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for modulus in [17, -17]:
        expression = _comparison(value, 3, 5, modulus)
        result = reverse_simplify(expression)
        assert _has_label(result, MIN_WIDTH)
        assert reverse_simplify(result) == result
        for concrete in [-1, 0, 32, 1 << 20]:
            substitution = Subst({'X': token(concrete)})
            # Preserve the original meaning at values excluded by the forward rule guards.
            assert reverse_simplify(substitution.apply(result)) == reverse_simplify(substitution.apply(expression))
    _assert_undefined(reverse_simplify, _comparison(value, 3, 5, 0))


def test_reverse_min_width_preserves_partial_operand(reverse_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    bounded = KApply('_modInt_', quotient, token(32))
    for bound in [-1, 0, 3, 5, 6]:
        result = reverse_simplify(_comparison(bounded, bound))
        assert reverse_simplify(result) == result
        _assert_undefined(reverse_simplify, Subst({'X': token(4), 'D': token(0)}).apply(result))
        assert reverse_simplify(Subst({'X': token(4), 'D': token(1)}).apply(result)) == token(2 > bound)


@pytest.mark.parametrize('node_id,count', [(18, 5), (26, 6)])
def test_actual_reverse_min_width_error_paths(reverse_explore: KCFGExplore, node_id: int, count: int) -> None:
    path = Path(__file__).parent / 'data' / f'half_two_reverse_node_{node_id}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == count
    state = CTerm(KApply('<generatedTop>'), constraints)
    assert isinstance(
        reverse_explore.kcfg_semantics.custom_step(state, reverse_explore.cterm_symbolic, node_id), Vacuous
    )
    assert set(state.constraints) == set(constraints)


@pytest.mark.parametrize('node_id', [19, 27])
def test_actual_reverse_min_width_feasible_paths(reverse_explore: KCFGExplore, node_id: int) -> None:
    path = Path(__file__).parent / 'data' / f'half_two_reverse_node_{node_id}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 5
    state = CTerm(KApply('<generatedTop>'), constraints)
    cs = reverse_explore.cterm_symbolic
    assert reverse_explore.kcfg_semantics.custom_step(state, cs, node_id) is None
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
    witness = Subst({'ARG_0': token(1 << 64)}).apply(mlAnd(constraints))
    concrete, _ = cs.kast_simplify(witness)
    assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
