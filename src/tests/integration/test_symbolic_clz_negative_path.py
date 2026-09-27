import json
from pathlib import Path

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, Subst
from pyk.kast.prelude.ml import is_top, mlAnd
from pyk.kast.prelude.utils import token
from pyk.kcfg.kcfg import Vacuous
from pyk.kore.rpc import SatResult

from komet.proof import _explore_context


@pytest.mark.parametrize('node_id', [22, 23])
def test_actual_negative_min_width_paths(node_id: int) -> None:
    path = Path(__file__).parent / 'data' / f'half_two_node_{node_id}_constraints.json'
    constraints = [KInner.from_dict(item) for item in json.loads(path.read_text())]
    assert len(constraints) == 5
    state = CTerm(KApply('<generatedTop>'), constraints)
    with _explore_context('negative-min-width-regression', None) as explore:
        cs = explore.cterm_symbolic
        step = explore.kcfg_semantics.custom_step(state, cs, node_id)
        if node_id == 23:
            assert isinstance(step, Vacuous)
        else:
            assert step is None
            normalized, _ = cs.kast_simplify(mlAnd(constraints))
            assert isinstance(cs._kore_client.get_model(cs.kast_to_kore(normalized)), SatResult)
            witness = Subst({'ARG_0': token(-(1 << 100))}).apply(mlAnd(constraints))
            concrete, _ = cs.kast_simplify(witness)
            assert is_top(concrete)
        assert set(state.constraints) == set(constraints)
