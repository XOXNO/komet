import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, KVariable, Subst
from pyk.kast.prelude.ml import is_bottom, is_top, mlAnd, mlCeil
from pyk.kast.prelude.utils import token
from pyk.kcfg import KCFGExplore
from pyk.kcfg.kcfg import Vacuous
from pyk.konvert import kast_to_kore, kore_to_kast
from pyk.kore.rpc import SatResult, UnsatResult

from komet.proof import _explore_context
from komet.utils import symbolic_definition


@pytest.fixture(scope="module")
def complement_explore() -> Iterator[KCFGExplore]:
    with _explore_context("masked-complement-regression", None) as explore:
        yield explore


@pytest.fixture(scope="module")
def complement_simplify(complement_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        pattern = kast_to_kore(definition, term)
        result = complement_explore.cterm_symbolic._kore_client.simplify(pattern)[0]
        return kore_to_kast(definition, result)

    return simplify


def _complement_and(value: KInner, mask: KInner, modulus: KInner, swapped: bool) -> KInner:
    complement = KApply("_modInt_", KApply("_xorInt_", value, mask), modulus)
    return KApply("_&Int_", value, complement) if swapped else KApply("_&Int_", complement, value)


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort="K")))


@pytest.mark.parametrize("swapped", [False, True])
def test_masked_complement_symbolic_and_idempotence(
    complement_simplify: Callable[[KInner], KInner], swapped: bool
) -> None:
    for modulus in [1, 2, 8, 1 << 32, 1 << 64]:
        result = complement_simplify(
            _complement_and(KVariable("X", "Int"), token(modulus - 1), token(modulus), swapped)
        )
        assert complement_simplify(result) == result
        if modulus > 1:
            assert result == token(0)
        else:
            # XOR-zero can erase the matching shape before this rule sees M=1.
            # Check retained semantics without requiring a particular normal form.
            for value in [-(1 << 127), -1, 0, 1, 1 << 127]:
                assert complement_simplify(Subst({"X": token(value)}).apply(result)) == token(0)


@pytest.mark.parametrize("swapped", [False, True])
def test_masked_complement_signed_extrema(
    complement_simplify: Callable[[KInner], KInner], swapped: bool
) -> None:
    for modulus in [1, 8, 1 << 64]:
        for value in [-(1 << 255), -(1 << 127), -(1 << 63), -modulus - 1, -1, 0, modulus - 1, 1 << 255]:
            assert ((value ^ (modulus - 1)) % modulus) & value == 0
            assert complement_simplify(
                _complement_and(token(value), token(modulus - 1), token(modulus), swapped)
            ) == token(0)


@pytest.mark.parametrize("swapped", [False, True])
def test_masked_complement_requires_complete_concrete_guards(
    complement_simplify: Callable[[KInner], KInner], swapped: bool
) -> None:
    value = KVariable("X", "Int")
    for modulus, mask in [(3, 2), (8, 6), (-8, -9)]:
        assert complement_simplify(_complement_and(value, token(mask), token(modulus), swapped)) != token(0)
    for mask, modulus in [(KVariable("MASK", "Int"), token(8)), (token(7), KVariable("M", "Int"))]:
        assert complement_simplify(_complement_and(value, mask, modulus, swapped)) != token(0)
    _assert_undefined(complement_simplify, _complement_and(value, token(-1), token(0), swapped))
    # Omitting the power-of-two or full-mask guard admits a nonzero counterexample.
    for x, modulus, mask in [(3, 3, 2), (1, 8, 6)]:
        expected = ((x ^ mask) % modulus) & x
        assert expected != 0
        assert complement_simplify(_complement_and(token(x), token(mask), token(modulus), swapped)) == token(expected)


@pytest.mark.parametrize("swapped", [False, True])
@pytest.mark.parametrize("modulus", [1, 8, 1 << 64])
def test_masked_complement_preserves_repeated_partial_operand(
    complement_simplify: Callable[[KInner], KInner], swapped: bool, modulus: int
) -> None:
    for division in ["_/Int_", "_divInt_"]:
        quotient = KApply(division, KVariable("X", "Int"), KVariable("D", "Int"))
        original = _complement_and(quotient, token(modulus - 1), token(modulus), swapped)
        result = complement_simplify(original)
        assert complement_simplify(result) == result
        # Substitute only after symbolic simplification; an erased ceil would lose D=0.
        undefined = Subst({"X": token(-7), "D": token(0)})
        _assert_undefined(complement_simplify, undefined.apply(result))
        _assert_undefined(complement_simplify, undefined.apply(original))
        defined = Subst({"X": token(-7), "D": token(1)})
        assert complement_simplify(defined.apply(result)) == token(0)
        assert complement_simplify(defined.apply(original)) == token(0)


@pytest.mark.parametrize("node_id", [28, 36])
def test_actual_masked_complement_error_paths(complement_explore: KCFGExplore, node_id: int) -> None:
    path = Path(__file__).parent / "data" / f"half_up_complement_node_{node_id}_constraints.json"
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 11
    state = CTerm(KApply("<generatedTop>"), constraints)
    cs = complement_explore.cterm_symbolic
    normalized = cs._kore_client.simplify(cs.kast_to_kore(mlAnd(constraints)))[0]
    assert isinstance(cs._kore_client.get_model(normalized), UnsatResult)
    assert isinstance(complement_explore.kcfg_semantics.custom_step(state, cs, node_id), Vacuous)
    assert set(state.constraints) == set(constraints)


@pytest.mark.parametrize("node_id", [24, 29])
def test_actual_masked_complement_feasible_paths(complement_explore: KCFGExplore, node_id: int) -> None:
    path = Path(__file__).parent / "data" / f"half_up_complement_node_{node_id}_constraints.json"
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == (10 if node_id == 24 else 11)
    state = CTerm(KApply("<generatedTop>"), constraints)
    cs = complement_explore.cterm_symbolic
    assert complement_explore.kcfg_semantics.custom_step(state, cs, node_id) is None
    normalized = cs._kore_client.simplify(cs.kast_to_kore(mlAnd(constraints)))[0]
    assert isinstance(cs._kore_client.get_model(normalized), SatResult)
    witness = Subst({"ARG_0": token(0), "ARG_1": token(0), "ARG_2": token(1 << 64)})
    concrete, _ = cs.kast_simplify(witness.apply(mlAnd(constraints)))
    assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
