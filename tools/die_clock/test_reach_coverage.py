import copy
import math

import pytest
from clock_reach_check import check


def manifest(length=150.):
    return dict(cells=[['drv','BUF',0.,0.]], sinks={'a':dict(x=length,y=0.)}, parent={'a':'drv'})


def test_complete_reach_and_boundary_comparison():
    assert check(manifest(405.))['verdict'] == 'PASS'
    assert check(manifest(405.+0.5e-6))['verdict'] == 'PASS'
    result = check(manifest(405.04))
    assert result['verdict'] == 'FAIL' and result['over_limit'] == 1
    assert result['max_raw_um'] == 405.04


def test_one_unknown_child_cannot_hide_behind_a_known_child():
    m = manifest();m['parent']['missing'] = 'drv'
    r = check(m)
    assert r['verdict'] == 'FAIL' and r['nets_without_xy'] == 1
    assert r['unknown_nets_sample'][0]['missing'] == ['missing']
    assert r['nets'] == 0  # incomplete net is never silently measured as a shorter net


def test_missing_driver_fails_even_with_known_load():
    m = manifest();m['cells'] = []
    r = check(m)
    assert r['verdict'] == 'FAIL' and r['nets_without_xy'] == 1


@pytest.mark.parametrize('coordinate', [float('nan'),float('inf'),-float('inf'),None,True])
def test_nonfinite_or_invalid_child_coordinate_refused(coordinate):
    m = manifest();m['sinks']['a']['x'] = coordinate
    assert check(m)['verdict'] == 'FAIL'


@pytest.mark.parametrize('m', [{}, {'parent':{}}, {'parent':{'a':'entry'},'local_root_xy':{'entry':[0.,0.]}}])
def test_empty_or_only_ideal_graph_is_not_reach_pass(m):
    assert check(m)['verdict'] == 'FAIL'


def test_actual_spine_source_coordinate_covers_non_tree_root():
    m = manifest();m['parent'] = {'drv':'core/pll_ck','a':'drv'}
    assert check(m)['verdict'] == 'FAIL'
    m['source_xy'] = {'core/pll_ck':[-5.,0.]}
    result = check(m)
    assert result['verdict'] == 'PASS' and result['nets'] == 2


def test_build_preserves_marginal_sink_coordinate():
    from build import sink_record
    sink = sink_record('tree',('a','leaf',405.0004,0.,'leaf/ck'),[0,0,0])
    assert sink['x'] == 405.0004
    m = manifest();m['sinks']['a'] = sink
    assert check(m)['verdict'] == 'FAIL'


def test_conflicting_duplicate_coordinates_are_not_silently_overwritten():
    m = manifest();m['source_xy'] = {'drv':[1.,0.]}
    result = check(m)
    assert result['verdict'] == 'FAIL' and 'drv' in result['invalid_coordinates']
