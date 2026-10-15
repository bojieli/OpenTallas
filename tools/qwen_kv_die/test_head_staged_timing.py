"""Admission checks must respect each physical launch/capture budget."""
import itertools
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import head_staged_plan as H


def test_native_budget_rejects_geometrically_short_wire():
    pairs=[('actual_stage_hop',[(0.,0.)],[(450.,0.)],427.)]
    effective=float(np.max(H.coefficients(pairs)))
    assert 450.<H.LIMIT and effective>H.LIMIT
    assert H.witness(pairs,(0.,0.))['setup_margin_ps']<0


def test_weighted_halfplanes_equal_direct_corner_slack():
    pairs=[('a',[(0.,0.),(2.,3.)],[(123.,27.),(120.,26.)],211.),
           ('b',[(9.,7.),(8.,9.)],[(18.,31.)],44.)]
    for xy in [(0.,0.),(20.,-30.),(-60.,70.)]:
        direct=max(abs(a[0]+xy[0]-b[0])+abs(a[1]+xy[1]-b[1])+H.LIMIT-cap
                   for _,aa,bb,cap in pairs for a,b in itertools.product(aa,bb))
        assert abs(float(np.max(np.array(xy)@H.SIGNS.T+H.coefficients(pairs)))-direct)<1e-9
        assert abs(H.witness(pairs,xy)['effective_um']-direct)<1e-6


def test_legacy_geometry_retains_unweighted_arithmetic():
    pair=[('legacy',[(0.,0.),(2.,3.)],[(123.,27.),(120.,26.)])]
    weighted=[(*p,H.LIMIT)for p in pair]
    np.testing.assert_array_equal(H.coefficients(pair),H.coefficients(weighted))
