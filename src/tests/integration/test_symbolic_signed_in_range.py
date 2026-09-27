import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, KLabel, KVariable, Subst
from pyk.kast.prelude.ml import is_bottom, is_top, mlAnd, mlBottom, mlCeil
from pyk.kast.prelude.utils import token
from pyk.kcfg import KCFGExplore
from pyk.kcfg.kcfg import Vacuous
from pyk.konvert import kast_to_kore, kore_to_kast
from pyk.kore.rpc import SatResult, UnsatResult

from komet.proof import _explore_context
from komet.utils import symbolic_definition


SIGNED = "#signed(_,_)_WASM-DATA-INTERNAL-SYNTAX_Int_IWidth_Int"
WIDTH_LABELS = {
    8: "i8_WASM-DATA-INTERNAL-SYNTAX_IWidth",
    16: "i16_WASM-DATA-INTERNAL-SYNTAX_IWidth",
    32: "i32",
    56: "i56_HOST-OBJECT_IWidth",
    64: "i64",
    128: "i128",
    256: "i256",
}


@pytest.fixture(scope="module")
def signed_range_explore() -> Iterator[KCFGExplore]:
    with _explore_context("signed-in-range-regression", None) as explore:
        yield explore


@pytest.fixture(scope="module")
def signed_range_simplify(signed_range_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        result = signed_range_explore.cterm_symbolic._kore_client.simplify(kast_to_kore(definition, term))[0]
        return kore_to_kast(definition, result)

    return simplify


def _width(width: int) -> KApply:
    return KApply(WIDTH_LABELS[width])


def _signed(width: int, value: KInner) -> KApply:
    return KApply(SIGNED, _width(width), value)


def _has_signed(term: KInner) -> bool:
    return (isinstance(term, KApply) and term.label.name in [SIGNED, "#signedTotal"]) or any(
        _has_signed(child) for child in term.terms
    )


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    # Equality-only SMT queries can leave an opaque partial function satisfiable.
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort="K")))


@pytest.mark.parametrize("width", WIDTH_LABELS)
def test_signed_all_actual_widths_and_boundaries(
    signed_range_simplify: Callable[[KInner], KInner], width: int
) -> None:
    modulus, half = 1 << width, 1 << (width - 1)
    value = KApply("_modInt_", KVariable("X", "Int"), token(modulus))
    original = _signed(width, value)
    result = signed_range_simplify(original)
    assert not _has_signed(result)
    assert signed_range_simplify(result) == result
    for raw in [-1, 0, half - 1, half, modulus - 1, modulus]:
        unsigned = raw % modulus
        expected = unsigned if unsigned < half else unsigned - modulus
        subst = Subst({"X": token(raw)})
        assert signed_range_simplify(subst.apply(result)) == token(expected)
        assert signed_range_simplify(subst.apply(original)) == token(expected)


def test_signed_keeps_original_partial_domain(signed_range_simplify: Callable[[KInner], KInner]) -> None:
    for width in WIDTH_LABELS:
        modulus = 1 << width
        original = _signed(width, KVariable("X", "Int"))
        result = signed_range_simplify(original)
        for value in [-modulus, -1, modulus, modulus + 1]:
            subst = Subst({"X": token(value)})
            _assert_undefined(signed_range_simplify, subst.apply(original))
            _assert_undefined(signed_range_simplify, subst.apply(result))
        for value in [0, modulus // 2, modulus - 1]:
            expected = value if value < modulus // 2 else value - modulus
            assert signed_range_simplify(Subst({"X": token(value)}).apply(result)) == token(expected)


@pytest.mark.parametrize("width", WIDTH_LABELS)
def test_signed_preserves_partial_integer_operand(
    signed_range_simplify: Callable[[KInner], KInner], width: int
) -> None:
    for division in ["_/Int_", "_divInt_"]:
        partial = KApply(division, KVariable("X", "Int"), KVariable("D", "Int"))
        original = _signed(width, KApply("_modInt_", partial, token(1 << width)))
        result = signed_range_simplify(original)
        assert signed_range_simplify(result) == result
        zero_divisor = Subst({"X": token(-1), "D": token(0)})
        _assert_undefined(signed_range_simplify, zero_divisor.apply(result))
        _assert_undefined(signed_range_simplify, zero_divisor.apply(original))
        for value in [-1, 1]:
            assert signed_range_simplify(Subst({"X": token(value), "D": token(1)}).apply(result)) == token(value)


def test_signed_symbolic_width_stays_guarded(signed_range_simplify: Callable[[KInner], KInner]) -> None:
    original = KApply(SIGNED, KVariable("W", "IWidth"), KVariable("X", "Int"))
    result = signed_range_simplify(original)
    assert _has_signed(result)
    for width in WIDTH_LABELS:
        assert signed_range_simplify(Subst({"W": _width(width), "X": token((1 << width) - 1)}).apply(result)) == token(-1)
        _assert_undefined(signed_range_simplify, Subst({"W": _width(width), "X": token(-1)}).apply(result))


def test_signed_preserves_partial_width_operand(signed_range_simplify: Callable[[KInner], KInner]) -> None:
    _assert_undefined(signed_range_simplify, KApply(SIGNED, mlBottom("IWidth"), token(0)))
    quotient = KApply("_/Int_", KVariable("X", "Int"), KVariable("D", "Int"))
    width = KApply(KLabel("ite", "IWidth"), KApply("_==Int_", quotient, token(0)), _width(128), _width(256))
    original = KApply(SIGNED, width, token(1 << 127))
    result = signed_range_simplify(original)
    assert signed_range_simplify(result) == result
    _assert_undefined(signed_range_simplify, Subst({"X": token(0), "D": token(0)}).apply(result))
    assert signed_range_simplify(Subst({"X": token(0), "D": token(1)}).apply(result)) == token(-(1 << 127))
    assert signed_range_simplify(Subst({"X": token(1), "D": token(1)}).apply(result)) == token(1 << 127)


def test_signed_and_existing_total_wrapper_agree(signed_range_simplify: Callable[[KInner], KInner]) -> None:
    for width in [32, 64]:
        value = KApply("_modInt_", KVariable("X", "Int"), token(1 << width))
        partial = signed_range_simplify(_signed(width, value))
        total = signed_range_simplify(KApply("#signedTotal", _width(width), value))
        assert partial == total
        assert not _has_signed(partial)


def test_actual_signed_storage_error_path(signed_range_explore: KCFGExplore) -> None:
    path = Path(__file__).parent / "data" / "storage_signed_node_9_constraints.json"
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 6
    state = CTerm(KApply("<generatedTop>"), constraints)
    cs = signed_range_explore.cterm_symbolic
    normalized = cs._kore_client.simplify(cs.kast_to_kore(mlAnd(constraints)))[0]
    assert isinstance(cs._kore_client.get_model(normalized), UnsatResult)
    assert isinstance(signed_range_explore.kcfg_semantics.custom_step(state, cs, 9), Vacuous)
    assert set(state.constraints) == set(constraints)


@pytest.mark.parametrize(
    "node_id,count,witnesses",
    [(1, 2, [-(1 << 127), (1 << 127) - 1, 0, -1]), (7, 3, [0, -1]), (8, 7, [1 << 60, -(1 << 60)])],
)
def test_actual_signed_storage_feasible_paths(
    signed_range_explore: KCFGExplore, node_id: int, count: int, witnesses: list[int]
) -> None:
    path = Path(__file__).parent / "data" / f"storage_signed_node_{node_id}_constraints.json"
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == count
    state = CTerm(KApply("<generatedTop>"), constraints)
    cs = signed_range_explore.cterm_symbolic
    assert signed_range_explore.kcfg_semantics.custom_step(state, cs, node_id) is None
    normalized = cs._kore_client.simplify(cs.kast_to_kore(mlAnd(constraints)))[0]
    assert isinstance(cs._kore_client.get_model(normalized), SatResult)
    for witness in witnesses:
        concrete, _ = cs.kast_simplify(Subst({"ARG_0": token(witness)}).apply(mlAnd(constraints)))
        assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
