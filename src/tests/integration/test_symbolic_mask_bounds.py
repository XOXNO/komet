from collections.abc import Callable, Iterator

import pytest
from pyk.kast.inner import KApply, KInner, KVariable, Subst, flatten_label
from pyk.kast.prelude.ml import is_bottom, mlAnd, mlCeil, mlEqualsTrue
from pyk.kast.prelude.utils import token
from pyk.konvert import kast_to_kore, kore_to_kast

from komet.proof import _explore_context
from komet.utils import symbolic_definition

MASK64 = (1 << 64) - 1
GET_RANGE = '#getRange(_,_,_)_WASM-DATA-COMMON_Int_SparseBytes_Int_Int'
SET_RANGE = '#setRange(_,_,_,_)_WASM-DATA-COMMON_SparseBytes_SparseBytes_Int_Int_Int'
SPARSE_NIL = '.List{"___SPARSE-BYTES-SYNTAX_SparseBytes_SBItemChunk_SparseBytes"}_SparseBytes'
UNSIGNED = '#unsigned(_,_)_WASM-DATA-INTERNAL-SYNTAX_Int_IWidth_Int'
WRAP = '#wrap(_,_)_WASM-DATA-COMMON_Int_Int_Int'


@pytest.fixture(scope='module')
def symbolic_simplify() -> Iterator[Callable[[KInner], KInner]]:
    # One backend session; no execution or proof advancement.
    definition = symbolic_definition().kdefinition
    with _explore_context('mask-bounds-regression', None) as explore:

        def simplify_term(term: KInner) -> KInner:
            pattern = kast_to_kore(definition, term)
            simplified = explore.cterm_symbolic._kore_client.simplify(pattern)[0]
            return kore_to_kast(definition, simplified)

        yield simplify_term


def _masked(value: KInner, mask: int) -> KApply:
    return KApply('_&Int_', value, token(mask))


def _bounds(value: KInner, mask: int) -> list[KInner]:
    masked = _masked(value, mask)
    return [KApply('_<=Int_', token(0), masked), KApply('_<Int_', masked, token(mask + 1))]


def _with_i128_domain(term: KInner, sort: str) -> KInner:
    # These are the original claim's full i128 bounds, required by #unsigned's ceil rule.
    constraints = [
        mlEqualsTrue(bound, sort=sort)
        for index in range(3)
        for bound in [
            KApply('_<=Int_', token(-(1 << 127)), KVariable(f'ARG_{index}', 'Int')),
            KApply('_<=Int_', KVariable(f'ARG_{index}', 'Int'), token((1 << 127) - 1)),
        ]
    ]
    return mlAnd([term, *constraints], sort=sort)


def test_symbolic_mask_bounds(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    expressions = [bound for mask in [0, 5, MASK64] for bound in _bounds(KVariable('X', 'Int'), mask)]
    for expression in expressions:
        assert is_bottom(symbolic_simplify(mlEqualsTrue(KApply('notBool_', expression))))


def test_guard_counterexamples(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    cases = [
        (KApply('_<=Int_', token(0), _masked(value, -1)), -1),
        (KApply('_<Int_', _masked(value, 7), token(7)), 7),
        (KApply('_<Int_', _masked(value, 7), token(6)), 6),
        (KApply('_<Int_', _masked(value, 7), token(0)), 0),
    ]
    for expression, counterexample in cases:
        simplified = symbolic_simplify(expression)
        assert simplified != token(True)
        assert symbolic_simplify(Subst({'X': token(counterexample)}).apply(simplified)) == token(False)


def test_partial_operands_remain_undefined(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    operands = [
        KApply('_/Int_', token(1), token(0)),
        KApply('_/Int_', value, token(0)),
        KApply('_modInt_', value, token(0)),
        KApply('_<<Int_', value, token(-1)),
    ]
    for operand in operands:
        for mask in [0, MASK64]:
            for expression in _bounds(operand, mask):
                simplified = symbolic_simplify(expression)
                assert simplified != token(True)
                assert is_bottom(simplified) or is_bottom(symbolic_simplify(mlCeil(simplified, arg_sort='K')))


def test_symbolic_denominator_keeps_definedness(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    quotient = KApply('_/Int_', KVariable('X', 'Int'), KVariable('D', 'Int'))
    for mask in [0, MASK64]:
        for expression in _bounds(quotient, mask):
            simplified = symbolic_simplify(expression)
            assert simplified != token(True)
            undefined = symbolic_simplify(Subst({'X': token(1), 'D': token(0)}).apply(simplified))
            assert is_bottom(undefined) or is_bottom(symbolic_simplify(mlCeil(undefined, arg_sort='K')))
            assert symbolic_simplify(Subst({'X': token(-2), 'D': token(1)}).apply(simplified)) == token(True)


def test_borrow_signed_comparison_frontier(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    high = _masked(KApply('_>>Int_', KVariable('ARG_0', 'Int'), token(64)), MASK64)
    comparison = KApply('intRelOp', KApply('i64'), KApply('intLt_s'), high, token(0))
    simplified = symbolic_simplify(comparison)
    assert isinstance(simplified, KApply) and simplified.label.name == 'IVal'
    assert simplified.args[0] == KApply('i32')
    for value in [-(1 << 127), -1, 0, (1 << 127) - 1]:
        concrete = symbolic_simplify(Subst({'ARG_0': token(value)}).apply(simplified))
        assert concrete == KApply('IVal', KApply('i32'), token(int(value < 0)))


def test_half_up_memory_frontier(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    # Exact nested-write shape at the half-up proof's signed-comparison frontier.
    memory = KApply(SPARSE_NIL)
    for index in range(3):
        value = KVariable(f'ARG_{index}', 'Int')
        high = _masked(KApply('_>>Int_', value, token(64)), MASK64)
        memory = KApply(SET_RANGE, memory, token(1048568), high, token(8))
        if index < 2:
            low = _masked(KApply(UNSIGNED, KApply('i128'), value), MASK64)
            memory = KApply(SET_RANGE, memory, token(1048560), low, token(8))
            memory = KApply(SET_RANGE, memory, token(1048544), token(0), token(8))
    read = KApply(GET_RANGE, memory, token(1048568), token(8))
    assert symbolic_simplify(_with_i128_domain(read, 'Int')) == symbolic_simplify(_with_i128_domain(high, 'Int'))
    comparison = KApply('intRelOp', KApply('i64'), KApply('intLt_s'), read, token(0))
    simplified = symbolic_simplify(_with_i128_domain(comparison, 'Val'))
    assert any(
        isinstance(term, KApply) and term.label.name == 'IVal' and term.args[0] == KApply('i32')
        for term in flatten_label('#And', simplified)
    )


def test_wrap_preserves_out_of_range_values(symbolic_simplify: Callable[[KInner], KInner]) -> None:
    value = KVariable('X', 'Int')
    for width, masked in [(1, _masked(value, 5)), (8, _masked(KApply('_>>Int_', value, token(64)), MASK64))]:
        assert symbolic_simplify(KApply(WRAP, token(width), masked)) == symbolic_simplify(masked)
    wrapped = symbolic_simplify(KApply(WRAP, token(1), value))
    assert wrapped != value
    for concrete, expected in [(-1, 255), (0, 0), (255, 255), (256, 0)]:
        assert symbolic_simplify(Subst({'X': token(concrete)}).apply(wrapped)) == token(expected)
    assert symbolic_simplify(KApply(WRAP, token(8), token(MASK64 + 1))) == token(0)
    for width in [0, -1]:
        assert symbolic_simplify(KApply(WRAP, token(width), token(1))) == token(0)
    for width in [0, 1]:
        partial = KApply(WRAP, token(width), KApply('_/Int_', value, token(0)))
        simplified = symbolic_simplify(partial)
        assert is_bottom(simplified) or is_bottom(symbolic_simplify(mlCeil(simplified, arg_sort='K')))
    quotient = KApply(WRAP, token(1), KApply('_/Int_', value, KVariable('D', 'Int')))
    simplified = symbolic_simplify(quotient)
    undefined = symbolic_simplify(Subst({'X': token(1), 'D': token(0)}).apply(simplified))
    assert is_bottom(undefined) or is_bottom(symbolic_simplify(mlCeil(undefined, arg_sort='K')))
    assert symbolic_simplify(Subst({'X': token(256), 'D': token(1)}).apply(simplified)) == token(0)
