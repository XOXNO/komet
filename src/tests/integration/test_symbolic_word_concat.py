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

UNSIGNED = '#unsigned(_,_)_WASM-DATA-INTERNAL-SYNTAX_Int_IWidth_Int'
BASE = 1 << 64


@pytest.fixture(scope='module')
def concat_explore() -> Iterator[KCFGExplore]:
    with _explore_context('word-concat-regression', None) as explore:
        yield explore


@pytest.fixture(scope='module')
def concat_simplify(concat_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        pattern = kast_to_kore(definition, term)
        result = concat_explore.cterm_symbolic._kore_client.simplify(pattern)[0]
        return kore_to_kast(definition, result)

    return simplify


def _has_label(term: KInner, label: str) -> bool:
    return (isinstance(term, KApply) and term.label.name == label) or any(
        _has_label(child, label) for child in term.terms
    )


def _pack(limbs: list[KInner]) -> KInner:
    result = KApply('_<<Int_', limbs[0], token(192))
    for limb, shift in zip(limbs[1:], [128, 64, 0], strict=True):
        result = KApply('_|Int_', result, KApply('_<<Int_', limb, token(shift)) if shift else limb)
    return result


def _weighted(limbs: list[KInner]) -> KInner:
    result = KApply('_*Int_', limbs[0], token(1 << 192))
    for limb, shift in zip(limbs[1:], [128, 64, 0], strict=True):
        result = KApply('_+Int_', result, KApply('_*Int_', limb, token(1 << shift)) if shift else limb)
    return result


def _under_unsigned_domain(term: KInner, value: KInner, width: int) -> KInner:
    return mlAnd(
        [
            term,
            mlEqualsTrue(KApply('_<=Int_', token(-(1 << (width - 1))), value), sort='Int'),
            mlEqualsTrue(KApply('_<Int_', value, token(1 << width)), sort='Int'),
        ],
        sort='Int',
    )


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort='K')))


def test_constant_right_shifts_are_euclidean(concat_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for shift in [0, 1, 63, 64, 127, 256]:
        result = concat_simplify(KApply('_>>Int_', value, token(shift)))
        assert result == concat_simplify(KApply('_divInt_', value, token(1 << shift)))
        for concrete in [-((1 << shift) + 1), -1, 0, (1 << shift) + 1]:
            assert concat_simplify(Subst({'X': token(concrete)}).apply(result)) == token(concrete >> shift)


def test_right_shift_guards_and_partiality(concat_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    symbolic = KApply('_>>Int_', value, KVariable('S', 'Int'))
    assert _has_label(concat_simplify(symbolic), '_>>Int_')
    _assert_undefined(concat_simplify, KApply('_>>Int_', value, token(-1)))
    quotient = KApply('_/Int_', value, KVariable('D', 'Int'))
    for shift in [0, 64]:
        result = concat_simplify(KApply('_>>Int_', quotient, token(shift)))
        # An unknown divisor may prevent normalization; undefinedness must survive either form.
        _assert_undefined(concat_simplify, Subst({'X': token(1), 'D': token(0)}).apply(result))
        assert concat_simplify(Subst({'X': token(-3), 'D': token(1)}).apply(result)) == token(-3 >> shift)


def test_unsigned_conversion_uses_full_defined_domain(concat_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for width in [32, 64, 128, 256]:
        bound = 1 << width
        expression = KApply(UNSIGNED, KApply(f'i{width}'), value)
        result = concat_simplify(_under_unsigned_domain(expression, value, width))
        assert not _has_label(result, UNSIGNED)
        for concrete in [-bound // 2, -1, 0, bound // 2, bound - 1]:
            assert concat_simplify(Subst({'X': token(concrete)}).apply(result)) == token(
                concrete + bound if concrete < 0 else concrete
            )
        # Neither outside endpoint belongs to the domain used to justify this rewrite.
        for concrete in [-bound // 2 - 1, bound]:
            assert is_bottom(concat_simplify(Subst({'X': token(concrete)}).apply(result)))
        assert _has_label(concat_simplify(expression), UNSIGNED)


def test_unsigned_conversion_preserves_partial_operand(concat_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    value = KApply('_-Int_', KApply('_modInt_', quotient, token(BASE)), token(BASE // 2))
    result = concat_simplify(KApply(UNSIGNED, KApply('i64'), value))
    _assert_undefined(concat_simplify, Subst({'X': token(1), 'D': token(0)}).apply(result))
    assert concat_simplify(Subst({'X': token(0), 'D': token(1)}).apply(result)) == token(BASE // 2)


def test_unsigned_conversion_requires_both_domain_bounds(concat_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    expression = KApply(UNSIGNED, KApply('i64'), value)
    for one_sided_bound in [
        KApply('_<=Int_', token(-BASE // 2), value),
        KApply('_<Int_', value, token(BASE)),
    ]:
        constrained = mlAnd([expression, mlEqualsTrue(one_sided_bound, sort='Int')], sort='Int')
        assert _has_label(concat_simplify(constrained), UNSIGNED)


def test_bounded_four_limb_packing(concat_simplify: Callable[[KInner], KInner]) -> None:
    limbs = [KApply('_modInt_', KVariable(f'X{i}', 'Int'), token(BASE)) for i in range(4)]
    result = concat_simplify(_pack(limbs))
    assert not _has_label(result, '_|Int_')
    assert result == concat_simplify(_weighted(limbs))
    for values in [[0] * 4, [BASE - 1] * 4, [1 << 63, 0, 0, 0], [-1, BASE, -BASE, BASE + 1]]:
        subst = Subst({f'X{i}': token(value) for i, value in enumerate(values)})
        expected = sum((value % BASE) << shift for value, shift in zip(values, [192, 128, 64, 0], strict=True))
        assert concat_simplify(subst.apply(result)) == token(expected)


def test_four_limb_packing_rejects_unbounded_or_invalid_limbs(concat_simplify: Callable[[KInner], KInner]) -> None:
    for index in range(4):
        limbs = [KApply('_modInt_', KVariable(f'X{i}', 'Int'), token(BASE)) for i in range(4)]
        # Exactly one limb lacks a range proof; the other three satisfy their guards.
        limbs[index] = KVariable(f'X{index}', 'Int')
        result = concat_simplify(_pack(limbs))
        assert _has_label(result, '_|Int_')
        for invalid in [-1, BASE]:
            values = [1] * 4
            values[index] = invalid
            subst = Subst({f'X{i}': token(value) for i, value in enumerate(values)})
            expected = (values[0] << 192) | (values[1] << 128) | (values[2] << 64) | values[3]
            assert concat_simplify(subst.apply(result)) == token(expected)
            if index > 0:
                assert expected != sum(value << shift for value, shift in zip(values, [192, 128, 64, 0], strict=True))


def test_four_limb_packing_preserves_partial_operands(concat_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    for index in range(4):
        limbs = [KApply('_modInt_', KVariable(f'X{i}', 'Int'), token(BASE)) for i in range(4)]
        limbs[index] = KApply('_modInt_', quotient, token(BASE))
        result = concat_simplify(_pack(limbs))
        subst = Subst({'X': token(1), 'D': token(0), **{f'X{i}': token(1) for i in range(4)}})
        _assert_undefined(concat_simplify, subst.apply(result))
        defined = Subst({'X': token(1), 'D': token(1), **{f'X{i}': token(1) for i in range(4)}})
        assert concat_simplify(defined.apply(result)) == token((1 << 192) + (1 << 128) + BASE + 1)


def test_four_limb_packing_requires_lower_and_upper_bounds(concat_simplify: Callable[[KInner], KInner]) -> None:
    for index in range(4):
        bounded = [KApply('_modInt_', KVariable(f'X{i}', 'Int'), token(BASE)) for i in range(4)]
        for invalid in [
            KApply('_-Int_', token(-1), bounded[index]),
            KApply('_+Int_', token(BASE), bounded[index]),
        ]:
            limbs = [*bounded]
            limbs[index] = invalid
            assert _has_label(concat_simplify(_pack(limbs)), '_|Int_')


def test_actual_half_up_error_path_is_infeasible(concat_explore: KCFGExplore) -> None:
    path = Path(__file__).parent / 'data' / 'half_up_node_45_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 12
    state = CTerm(KApply('<generatedTop>'), constraints)
    step = concat_explore.kcfg_semantics.custom_step(state, concat_explore.cterm_symbolic, 45)
    assert isinstance(step, Vacuous)
    assert set(state.constraints) == set(constraints)


def test_xor_zero_identities(concat_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for expression in [KApply('_xorInt_', value, token(0)), KApply('_xorInt_', token(0), value)]:
        assert concat_simplify(expression) == value
        for concrete in [-(1 << 256), -1, 0, 1, (1 << 256) - 1]:
            assert concat_simplify(Subst({'X': token(concrete)}).apply(expression)) == token(concrete)
    nonzero = KApply('_xorInt_', value, token(1))
    assert _has_label(concat_simplify(nonzero), '_xorInt_')
    assert concat_simplify(Subst({'X': token(-1)}).apply(nonzero)) == token(-2)


def test_xor_zero_preserves_partial_operands(concat_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    for expression in [KApply('_xorInt_', quotient, token(0)), KApply('_xorInt_', token(0), quotient)]:
        result = concat_simplify(expression)
        _assert_undefined(concat_simplify, Subst({'X': token(1), 'D': token(0)}).apply(result))
        assert concat_simplify(Subst({'X': token(-3), 'D': token(1)}).apply(result)) == token(-3)


def test_actual_half_two_xor_error_path_is_infeasible(concat_explore: KCFGExplore) -> None:
    path = Path(__file__).parent / 'data' / 'half_two_node_46_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 6
    state = CTerm(KApply('<generatedTop>'), constraints)
    assert isinstance(concat_explore.kcfg_semantics.custom_step(state, concat_explore.cterm_symbolic, 46), Vacuous)
    assert set(state.constraints) == set(constraints)


def test_actual_half_two_feasible_sibling_is_preserved(concat_explore: KCFGExplore) -> None:
    path = Path(__file__).parent / 'data' / 'half_two_node_45_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 6
    state = CTerm(KApply('<generatedTop>'), constraints)
    cs = concat_explore.cterm_symbolic
    assert concat_explore.kcfg_semantics.custom_step(state, cs, 45) is None
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
    witness = Subst({'ARG_0': token(-(1 << 100))}).apply(mlAnd(constraints))
    concrete, _ = cs.kast_simplify(witness)
    assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
