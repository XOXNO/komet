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

BASE = 1 << 64


@pytest.fixture(scope='module')
def pack_explore() -> Iterator[KCFGExplore]:
    with _explore_context('pack-two-regression', None) as explore:
        yield explore


@pytest.fixture(scope='module')
def pack_simplify(pack_explore: KCFGExplore) -> Callable[[KInner], KInner]:
    definition = symbolic_definition().kdefinition

    def simplify(term: KInner) -> KInner:
        result = pack_explore.cterm_symbolic._kore_client.simplify(kast_to_kore(definition, term))[0]
        return kore_to_kast(definition, result)

    return simplify


def _has_or(term: KInner) -> bool:
    return (isinstance(term, KApply) and term.label.name == '_|Int_') or any(_has_or(c) for c in term.terms)


def _pack(high: KInner, low: KInner, shift: int | KInner = 64) -> KInner:
    return KApply('_|Int_', KApply('_<<Int_', high, token(shift) if isinstance(shift, int) else shift), low)


def _weighted(high: KInner, low: KInner, width: int = 64) -> KInner:
    return KApply('_+Int_', KApply('_*Int_', high, token(1 << width)), low)


def _bounded(name: str, width: int = 64) -> KInner:
    return KApply('_modInt_', KVariable(name, 'Int'), token(1 << width))


def _assert_undefined(simplify: Callable[[KInner], KInner], term: KInner) -> None:
    result = simplify(term)
    assert is_bottom(result) or is_bottom(simplify(mlCeil(result, arg_sort='K')))


@pytest.mark.parametrize('width', [0, 1, 32, 64, 128, 192])
def test_word_pack_signed_high_and_idempotent(pack_simplify: Callable[[KInner], KInner], width: int) -> None:
    high, low = KVariable('H', 'Int'), (_bounded('L', width) if width else token(0))
    result = pack_simplify(_pack(high, low, width))
    assert not _has_or(result)
    if width == 0:
        # The packed term becomes H; the arithmetic helper can retain H * 1.
        assert result == high
    else:
        assert result == pack_simplify(_weighted(high, low, width))
    assert pack_simplify(result) == result
    bound = 1 << width
    for h, l in [(0, 0), (0, bound - 1), (-1, 0), (-1, bound - 1), (-(1 << 255), bound - 1), ((1 << 255), bound - 1), (1 << 63, 1 << 63), (-bound, bound + 1)]:
        subst = Subst({'H': token(h), 'L': token(l)})
        expected = (h << width) | (l % bound)
        assert pack_simplify(subst.apply(result)) == token(expected)
        assert pack_simplify(subst.apply(_pack(high, low, width))) == token(expected)


@pytest.mark.parametrize('width', [1, 32, 64, 128])
def test_word_pack_requires_low_lower_and_upper_bound(
    pack_simplify: Callable[[KInner], KInner], width: int
) -> None:
    high, low, bound = KVariable('H', 'Int'), KVariable('L', 'Int'), 1 << width
    for guard in [KApply('_<=Int_', token(0), low), KApply('_<Int_', low, token(bound))]:
        constrained = mlAnd([_pack(high, low, width), mlEqualsTrue(guard, sort='Int')], sort='Int')
        assert _has_or(pack_simplify(constrained))
    for outside in [KApply('_-Int_', token(-1), _bounded('OUT', width)), KApply('_+Int_', token(bound), _bounded('OUT', width))]:
        assert _has_or(pack_simplify(_pack(high, outside, width)))
    result = pack_simplify(_pack(high, low, width))
    assert _has_or(result)
    for outside in [-1, bound]:
        actual = (1 << width) | outside
        assert actual != bound + outside
        assert pack_simplify(Subst({'H': token(1), 'L': token(outside)}).apply(result)) == token(actual)


def test_word_pack_requires_nonnegative_concrete_width(pack_simplify: Callable[[KInner], KInner]) -> None:
    high, low = KVariable('H', 'Int'), _bounded('L')
    assert _has_or(pack_simplify(_pack(high, low, KVariable('W', 'Int'))))
    _assert_undefined(pack_simplify, _pack(high, low, -1))
    # A 64-bit low limb does not justify the width32 guard.
    result = pack_simplify(_pack(high, low, 32))
    assert _has_or(result)
    assert pack_simplify(Subst({'H':token(1), 'L':token(BASE - 1)}).apply(result)) == token(BASE - 1)
    # Width0 permits only low=0; negative and positive outside values stay ordinary ORs.
    for outside in [-1, 1]:
        result = pack_simplify(_pack(high, token(outside), 0))
        assert _has_or(result)
        assert pack_simplify(Subst({'H':token(1)}).apply(result)) == token(1 | outside)


def test_nested_word_packing(pack_simplify: Callable[[KInner], KInner]) -> None:
    high = KVariable('H', 'Int')
    middle, low = _bounded('M', 32), _bounded('L', 32)
    original = _pack(_pack(high, middle, 32), low, 32)
    result = pack_simplify(original)
    assert not _has_or(result)
    assert pack_simplify(result) == result
    for h,m,l in [(-1,0,0), (-(1 << 127),-1,1), (1 << 255, (1 << 32)-1, -1)]:
        subst=Subst({'H':token(h),'M':token(m),'L':token(l)})
        expected=(h << 64) + (m % (1 << 32)) * (1 << 32) + l % (1 << 32)
        assert pack_simplify(subst.apply(original)) == token(expected)
        assert pack_simplify(subst.apply(result)) == token(expected)


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('division', ['_/Int_', '_divInt_'])
def test_pack_two_preserves_each_partial_operand(
    pack_simplify: Callable[[KInner], KInner], index: int, division: str
) -> None:
    limbs = [KVariable('H', 'Int'), _bounded('L')]
    quotient = KApply(division, KVariable('X', 'Int'), KVariable('D', 'Int'))
    limbs[index] = quotient if index == 0 else KApply('_modInt_', quotient, token(BASE))
    original = _pack(*limbs)
    result = pack_simplify(original)
    assert pack_simplify(result) == result
    nonzero_divisor = KApply('_=/=Int_', KVariable('D', 'Int'), token(0))
    defined_domain = mlAnd([original, mlEqualsTrue(nonzero_divisor, sort='Int')], sort='Int')
    defined_result = pack_simplify(defined_domain)
    assert not _has_or(defined_result)
    assert pack_simplify(defined_result) == defined_result
    undefined = Subst({'H': token(1), 'L': token(1), 'X': token(-1), 'D': token(0)})
    _assert_undefined(pack_simplify, undefined.apply(original))
    _assert_undefined(pack_simplify, undefined.apply(result))
    _assert_undefined(pack_simplify, undefined.apply(defined_result))
    defined = Subst({'H': token(1), 'L': token(1), 'X': token(-1), 'D': token(1)})
    h, l = (-1, 1) if index == 0 else (1, BASE - 1)
    assert pack_simplify(defined.apply(original)) == token((h << 64) | l)
    assert pack_simplify(defined.apply(result)) == token((h << 64) | l)
    assert pack_simplify(defined.apply(defined_result)) == token((h << 64) | l)


def _constraints(node_id: int) -> list[KInner]:
    path = Path(__file__).parent / 'data' / f'storage_pack_node_{node_id}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == (5 if node_id == 12 else 4)
    return constraints


def test_actual_storage_constructor_error_path(pack_explore: KCFGExplore) -> None:
    constraints = _constraints(9)
    state = CTerm(KApply('<generatedTop>'), constraints)
    cs = pack_explore.cterm_symbolic
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), UnsatResult)
    assert isinstance(pack_explore.kcfg_semantics.custom_step(state, cs, 9), Vacuous)
    assert set(state.constraints) == set(constraints)


@pytest.mark.parametrize('node_id,witnesses', [(10, [1 << 64, -(1 << 127)]), (11, [0, -1]), (12, [1 << 60])])
def test_actual_storage_feasible_siblings(
    pack_explore: KCFGExplore, node_id: int, witnesses: list[int]
) -> None:
    constraints = _constraints(node_id)
    state = CTerm(KApply('<generatedTop>'), constraints)
    cs = pack_explore.cterm_symbolic
    assert pack_explore.kcfg_semantics.custom_step(state, cs, node_id) is None
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
    for witness in witnesses:
        concrete, _ = cs.kast_simplify(Subst({'ARG_0': token(witness)}).apply(mlAnd(constraints)))
        assert is_top(concrete)
    assert set(state.constraints) == set(constraints)


def test_actual_half_two_width32_path_stays_feasible(pack_explore: KCFGExplore) -> None:
    path = Path(__file__).parent / 'data' / 'half_two_pack_node_13_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 4
    cs = pack_explore.cterm_symbolic
    state = CTerm(KApply('<generatedTop>'), constraints)
    assert pack_explore.kcfg_semantics.custom_step(state, cs, 13) is None
    normalized, _ = cs.kast_simplify(mlAnd(constraints))
    assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
    concrete, _ = cs.kast_simplify(Subst({'ARG_0':token(1 << 64)}).apply(mlAnd(constraints)))
    assert is_top(concrete)
    assert set(state.constraints) == set(constraints)
