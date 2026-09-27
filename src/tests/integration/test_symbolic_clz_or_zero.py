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
from pyk.kore.rpc import SatResult

from komet.proof import _explore_context
from komet.utils import symbolic_definition

MIN_WIDTH = '#minWidth(_)_WASM-NUMERIC_Int_Int'


@pytest.fixture(scope='module')
def arithmetic_explore() -> Iterator[KCFGExplore]:
    with _explore_context('clz-or-zero-regression', None) as explore:
        yield explore


@pytest.fixture(scope='module')
def arithmetic_simplify(arithmetic_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        pattern = kast_to_kore(definition, term)
        result = arithmetic_explore.cterm_symbolic._kore_client.simplify(pattern)[0]
        return kore_to_kast(definition, result)

    return simplify


def _has_label(term: KInner, label: str) -> bool:
    return (isinstance(term, KApply) and term.label.name == label) or any(
        _has_label(child, label) for child in term.terms
    )


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort='K')))


def _comparison(value: KInner, bound: int, offset: int, modulus: int) -> KInner:
    return KApply(
        '_>Int_',
        token(bound),
        KApply('_modInt_', KApply('_-Int_', token(offset), KApply(MIN_WIDTH, value)), token(modulus)),
    )


def _or_zero(left: KInner, right: KInner, modulus: KInner, reverse: bool = False) -> KInner:
    masked = KApply('_modInt_', KApply('_|Int_', left, right), modulus)
    return KApply('_==Int_', token(0), masked) if reverse else KApply('_==Int_', masked, token(0))


def test_bounded_min_width_comparison_all_arms(arithmetic_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for offset, modulus in [(0, 1), (0, 17), (5, 17), (-12, 17), (22, 17), (130, 257)]:
        width = offset % modulus
        bounded = KApply('_modInt_', value, token(1 << width))
        for bound in [-1, 0, 1, width, width + 1]:
            result = arithmetic_simplify(_comparison(bounded, bound, offset, modulus))
            assert not _has_label(result, MIN_WIDTH)
            if bound <= 0:
                assert result == token(False)
            elif bound > width:
                assert result == token(True)
            else:
                expected = KApply('_>=Int_', bounded, token(1 << (width - bound)))
                assert result == arithmetic_simplify(expected)
            for concrete in [0, 1, (1 << max(width - 1, 0)) - 1, 1 << max(width - 1, 0), (1 << width) - 1, -1]:
                n = concrete % (1 << width)
                assert arithmetic_simplify(Subst({'X': token(concrete)}).apply(result)) == token(
                    bound > ((offset - n.bit_length()) % modulus)
                )


def test_min_width_comparison_requires_complete_domain(arithmetic_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    expression = _comparison(value, 3, 5, 17)
    assert _has_label(arithmetic_simplify(expression), MIN_WIDTH)
    for bound in [KApply('_<=Int_', token(0), value), KApply('_<Int_', value, token(32))]:
        constrained = mlAnd([expression, mlEqualsTrue(bound, sort='Bool')], sort='Bool')
        assert _has_label(arithmetic_simplify(constrained), MIN_WIDTH)
    # The excluded endpoints retain the source meaning, including negative minWidth = -1.
    for concrete in [-1, 32, 1 << 20]:
        width = -1 if concrete < 0 else concrete.bit_length()
        result = arithmetic_simplify(Subst({'X': token(concrete)}).apply(expression))
        assert result == token(3 > ((5 - width) % 17))
    for modulus in [0, -17]:
        result = arithmetic_simplify(_comparison(value, 3, 5, modulus))
        if modulus == 0:
            _assert_undefined(arithmetic_simplify, result)
        else:
            assert _has_label(result, MIN_WIDTH)


def test_min_width_constant_arms_preserve_partial_operand(arithmetic_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    bounded = KApply('_modInt_', quotient, token(32))
    for bound in [-1, 0, 3, 6]:
        result = arithmetic_simplify(_comparison(bounded, bound, 5, 17))
        _assert_undefined(arithmetic_simplify, Subst({'X': token(4), 'D': token(0)}).apply(result))
        assert arithmetic_simplify(Subst({'X': token(4), 'D': token(1)}).apply(result)) == token(bound > 2)


def test_masked_or_zero_signed_operands(arithmetic_simplify: Callable[[KInner], KInner]) -> None:
    left, right = KVariable('A', 'Int'), KVariable('B', 'Int')
    for modulus in [1, 2, 8, 1 << 64]:
        for reverse in [False, True]:
            result = arithmetic_simplify(_or_zero(left, right, token(modulus), reverse))
            assert not _has_label(result, '_|Int_')
            expected = KApply(
                '_andBool_',
                KApply('_==Int_', KApply('_modInt_', left, token(modulus)), token(0)),
                KApply('_==Int_', KApply('_modInt_', right, token(modulus)), token(0)),
            )
            assert result == arithmetic_simplify(expected)
            for a, b in [(0, 0), (-modulus, modulus), (-1, 0), (1, 2), (modulus, -modulus - 1)]:
                assert arithmetic_simplify(Subst({'A': token(a), 'B': token(b)}).apply(result)) == token(
                    ((a | b) % modulus) == 0
                )


def test_masked_or_zero_requires_positive_power_of_two(arithmetic_simplify: Callable[[KInner], KInner]) -> None:
    left, right = KVariable('A', 'Int'), KVariable('B', 'Int')
    for modulus in [-8, -3, 3, 6]:
        for reverse in [False, True]:
            result = arithmetic_simplify(_or_zero(left, right, token(modulus), reverse))
            assert _has_label(result, '_|Int_')
    result = arithmetic_simplify(_or_zero(left, right, KVariable('M', 'Int')))
    assert _has_label(result, '_|Int_')
    _assert_undefined(arithmetic_simplify, _or_zero(left, right, token(0)))
    # 1 | 2 = 3: zero modulo three despite neither operand being zero modulo three.
    assert arithmetic_simplify(_or_zero(token(1), token(2), token(3))) == token(True)
    assert (1 % 3 == 0 and 2 % 3 == 0) is False


def test_masked_or_zero_preserves_partial_operands(arithmetic_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    for modulus in [1, 8]:
        for other in [0, 1]:
            for reverse in [False, True]:
                for operands in [(quotient, token(other)), (token(other), quotient)]:
                    result = arithmetic_simplify(_or_zero(*operands, token(modulus), reverse))
                    _assert_undefined(arithmetic_simplify, Subst({'X': token(8), 'D': token(0)}).apply(result))
                    assert arithmetic_simplify(Subst({'X': token(8), 'D': token(1)}).apply(result)) == token(
                        ((8 | other) % modulus) == 0
                    )


@pytest.mark.parametrize('name,node_id,count', [('half_two_node_27', 27, 5), ('borrow_double_node_29', 29, 6)])
def test_actual_arithmetic_error_path_is_infeasible(
    arithmetic_explore: KCFGExplore, name: str, node_id: int, count: int
) -> None:
    path = Path(__file__).parent / 'data' / f'{name}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == count
    state = CTerm(KApply('<generatedTop>'), constraints)
    assert isinstance(
        arithmetic_explore.kcfg_semantics.custom_step(state, arithmetic_explore.cterm_symbolic, node_id), Vacuous
    )
    assert set(state.constraints) == set(constraints)


def test_actual_min_width_feasible_sibling_is_preserved(arithmetic_explore: KCFGExplore) -> None:
    path = Path(__file__).parent / 'data' / 'half_two_node_26_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 5
    state = CTerm(KApply('<generatedTop>'), constraints)
    cs = arithmetic_explore.cterm_symbolic
    assert arithmetic_explore.kcfg_semantics.custom_step(state, cs, 26) is None
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
    witness = Subst({'ARG_0': token(1 << 65)}).apply(mlAnd(constraints))
    concrete, _ = cs.kast_simplify(witness)
    assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
