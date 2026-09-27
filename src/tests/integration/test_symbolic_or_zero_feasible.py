import json
from pathlib import Path

from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, Subst
from pyk.kast.prelude.ml import is_top, mlAnd
from pyk.kast.prelude.utils import token
from pyk.kore.rpc import SatResult

from komet.proof import _explore_context


def test_actual_borrow_or_zero_feasible_path_is_preserved() -> None:
    # Node29's immediate sibling28 shares its impossible ancestor; node30 is feasible.
    path = Path(__file__).parent / 'data' / 'borrow_double_node_30_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 6
    state = CTerm(KApply('<generatedTop>'), constraints)
    with _explore_context('or-zero-feasible-regression', None) as explore:
        cs = explore.cterm_symbolic
        assert explore.kcfg_semantics.custom_step(state, cs, 30) is None
        normalized, _ = cs.kast_simplify(mlAnd(constraints))
        assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
        witness = Subst({'ARG_0': token(10**36)}).apply(mlAnd(constraints))
        concrete, _ = cs.kast_simplify(witness)
        assert is_top(concrete)
        assert set(state.constraints) == set(constraints)
