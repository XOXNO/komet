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


@pytest.fixture(scope="module")
def xor_explore() -> Iterator[KCFGExplore]:
    with _explore_context("xor-sign-regression", None) as explore:
        yield explore


@pytest.fixture(scope="module")
def xor_simplify(xor_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        pattern = kast_to_kore(definition, term)
        result = xor_explore.cterm_symbolic._kore_client.simplify(pattern)[0]
        return kore_to_kast(definition, result)

    return simplify


def _has_xor(term: KInner) -> bool:
    return (isinstance(term, KApply) and term.label.name == "_xorInt_") or any(_has_xor(child) for child in term.terms)


def _sign(value: KInner, bound: KInner, modulus: KInner) -> KInner:
    return KApply("_<Int_", KApply("_modInt_", value, modulus), bound)


def _xor_sign(left: KInner, right: KInner, bound: KInner, modulus: KInner) -> KInner:
    return _sign(KApply("_xorInt_", left, right), bound, modulus)


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort="K")))


def test_xor_sign_signed_operands_and_idempotence(
    xor_simplify: Callable[[KInner], KInner], xor_explore: KCFGExplore
) -> None:
    left, right = KVariable("X", "Int"), KVariable("Y", "Int")
    for bound in [1, 2, 8, 1 << 31, 1 << 63]:
        modulus = 2 * bound
        result = xor_simplify(_xor_sign(left, right, token(bound), token(modulus)))
        assert not _has_xor(result)
        assert xor_simplify(result) == result
        expected = KApply(
            "_==Bool_",
            _sign(left, token(bound), token(modulus)),
            _sign(right, token(bound), token(modulus)),
        )
        cs = xor_explore.cterm_symbolic
        normalized, _ = cs.kast_simplify(mlEqualsTrue(KApply("_=/=Bool_", result, expected)))
        assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), UnsatResult)
        for x, y in [
            (0, 0),
            (bound - 1, bound),
            (bound, bound),
            (-1, 0),
            (-bound, -1),
            (-modulus - 1, modulus),
        ]:
            assert xor_simplify(Subst({"X": token(x), "Y": token(y)}).apply(result)) == token(
                ((x ^ y) % modulus) < bound
            )


def test_xor_sign_constant_operand_orientations(
    xor_simplify: Callable[[KInner], KInner],
) -> None:
    value = KVariable("X", "Int")
    bound, modulus = 8, 16
    for constant in [0, 1, bound - 1, bound, modulus - 1, -1, -bound, -bound - 1]:
        for left, right in [(value, token(constant)), (token(constant), value)]:
            result = xor_simplify(_xor_sign(left, right, token(bound), token(modulus)))
            assert not _has_xor(result)
            assert xor_simplify(result) == result
            for x in [-17, 0, bound, modulus - 1]:
                assert xor_simplify(Subst({"X": token(x)}).apply(result)) == token(((x ^ constant) % modulus) < bound)


def test_xor_sign_requires_complete_guards(
    xor_simplify: Callable[[KInner], KInner],
) -> None:
    left, right = KVariable("X", "Int"), KVariable("Y", "Int")
    for bound, modulus in [(0, 2), (-4, -8)]:
        result = xor_simplify(_xor_sign(left, right, token(bound), token(modulus)))
        assert result == token(False) or _has_xor(result)
    for bound, modulus in [(3, 6), (2, 3), (2, -4)]:
        assert _has_xor(xor_simplify(_xor_sign(left, right, token(bound), token(modulus))))
    assert _has_xor(xor_simplify(_xor_sign(left, right, KVariable("B", "Int"), token(16))))
    assert _has_xor(xor_simplify(_xor_sign(left, right, token(8), KVariable("M", "Int"))))
    _assert_undefined(xor_simplify, _xor_sign(left, right, token(8), token(0)))
    # Removing either the power-of-two or the modulus guard makes the identity false.
    for bound, modulus, x, y in [(3, 6, 2, 1), (4, 6, 4, 2)]:
        actual = ((x ^ y) % modulus) < bound
        invalid = ((x % modulus) < bound) == ((y % modulus) < bound)
        assert actual != invalid
        assert xor_simplify(_xor_sign(token(x), token(y), token(bound), token(modulus))) == token(actual)


def test_xor_sign_preserves_partial_repeated_operand(
    xor_simplify: Callable[[KInner], KInner],
) -> None:
    quotient = KApply("_/Int_", KVariable("X", "Int"), KVariable("D", "Int"))
    for bound in [1, 8, 1 << 63]:
        result = xor_simplify(_xor_sign(quotient, quotient, token(bound), token(2 * bound)))
        assert xor_simplify(result) == result
        _assert_undefined(xor_simplify, Subst({"X": token(9), "D": token(0)}).apply(result))
        assert xor_simplify(Subst({"X": token(9), "D": token(1)}).apply(result)) == token(True)


def test_xor_sign_preserves_each_partial_operand(
    xor_simplify: Callable[[KInner], KInner],
) -> None:
    left = KApply("_/Int_", KVariable("X", "Int"), KVariable("D", "Int"))
    right = KApply("_/Int_", KVariable("Y", "Int"), KVariable("E", "Int"))
    for operands in [(left, right), (left, token(-1)), (token(-1), left)]:
        result = xor_simplify(_xor_sign(*operands, token(8), token(16)))
        assert xor_simplify(result) == result
        _assert_undefined(
            xor_simplify,
            Subst({"X": token(1), "Y": token(-1), "D": token(0), "E": token(1)}).apply(result),
        )
        if operands == (left, right):
            _assert_undefined(
                xor_simplify,
                Subst({"X": token(1), "Y": token(-1), "D": token(1), "E": token(0)}).apply(result),
            )
        assert xor_simplify(
            Subst({"X": token(1), "Y": token(-1), "D": token(1), "E": token(1)}).apply(result)
        ) == token(False)


def test_nested_xor_sign_terminates(xor_simplify: Callable[[KInner], KInner]) -> None:
    left, right, third = (KVariable(name, "Int") for name in ["X", "Y", "Z"])
    result = xor_simplify(_xor_sign(KApply("_xorInt_", left, right), third, token(8), token(16)))
    assert not _has_xor(result)
    assert xor_simplify(result) == result
    for x, y, z in [(1, 8, 15), (-1, 16, 8), (-9, -17, -1)]:
        assert xor_simplify(Subst({"X": token(x), "Y": token(y), "Z": token(z)}).apply(result)) == token(
            ((x ^ y ^ z) % 16) < 8
        )


@pytest.mark.parametrize("node_id", [26, 27, 30, 31])
def test_actual_xor_sign_error_paths(xor_explore: KCFGExplore, node_id: int) -> None:
    path = Path(__file__).parent / "data" / f"borrow_xor_sign_node_{node_id}_constraints.json"
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 7
    state = CTerm(KApply("<generatedTop>"), constraints)
    assert isinstance(
        xor_explore.kcfg_semantics.custom_step(state, xor_explore.cterm_symbolic, node_id),
        Vacuous,
    )
    assert set(state.constraints) == set(constraints)


@pytest.mark.parametrize(
    "node_id,witness",
    [
        (24, 2 * 10**27),
        (25, 10**27),
        (28, 999999999999999998596250399154372608),
        (29, 10**36),
    ],
)
def test_actual_xor_sign_feasible_paths(xor_explore: KCFGExplore, node_id: int, witness: int) -> None:
    path = Path(__file__).parent / "data" / f"borrow_xor_sign_node_{node_id}_constraints.json"
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 7
    state = CTerm(KApply("<generatedTop>"), constraints)
    cs = xor_explore.cterm_symbolic
    assert xor_explore.kcfg_semantics.custom_step(state, cs, node_id) is None
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
    concrete, _ = cs.kast_simplify(Subst({"ARG_0": token(witness)}).apply(mlAnd(constraints)))
    assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
