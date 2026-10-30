"""Die-edge PHY row margins are explicit per type and leave default kits unchanged."""
import copy
import json
from pathlib import Path

import pytest
import gen_phys as G
import schema as S


def test_default_core_area_matches_previous_emission():
    t=dict(outline_um=[777.6,1641.6])
    assert ' '.join(G._um(v) for v in G.kit_core_area(t)) == '4.32 4.32 773.28 1637.28'
    assert 'kit_core_margins_um' not in t


def test_coll_ucie_phy_fits_without_moving_macro_or_outline():
    t=dict(outline_um=[777.6,1641.6],kit_core_margins_um=[0,0,0,4.32],
           contents=[dict(origin_um=[0,0],outline_um=[777.6,777.6])])
    before=copy.deepcopy(t)
    x0,y0,x1,y1=G.kit_core_area(t)
    assert [x0,y0,x1,y1] == [0,0,777.6,1637.28]
    mx,my=t['contents'][0]['origin_um'];mw,mh=t['contents'][0]['outline_um']
    assert x0<=mx and y0<=my and mx+mw<=x1 and my+mh<=y1
    assert t==before


@pytest.mark.parametrize('m',[[0,0,0],[-.054,0,0,0],[0,.1,0,0],[1,0,0,0],[True,0,0,0],[0,0,0,float('nan')],[777.6,0,0,0]])
def test_invalid_margins_fail(m):
    with pytest.raises(ValueError):G.kit_core_area(dict(outline_um=[777.6,1641.6],kit_core_margins_um=m))


def test_schema_accepts_explicit_type_margin():
    p=json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
    tn=next(iter(p['partition_types']))
    p['partition_types'][tn]['kit_core_margins_um']=[0,0,0,4.32]
    assert not S.validate_structure(p)
    p['partition_types'][tn]['kit_core_margins_um']=[0,0,0]
    assert S.validate_structure(p)
