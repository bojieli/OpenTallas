from pathlib import Path
import copy
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import landing_place as L

RID = r'u_core\.u\.u_lep\.u\.rid\\\[[0-9]+\\\]\$_DFF_P_'


def typ(mode='cell'):
    return {'outline_um': [200, 100], 'contents': [{'inst': 'u_core', 'module': 'dut', 'params': {}}],
            'clock': {'landing_contract': {'native_stage_groups': {
                'schema': 'opentallas.native_stage_groups.v1', 'content': 'u_core', 'module': 'dut', 'params': {},
                'groups': [{'prefix': RID, 'rect_um': [10, 10, 70, 45], 'tag': 'stage:hub_rid', 'match': mode}]}}}}


def script(t):
    _, check = L._native_stage_groups(t, [])
    s = L._native_stage_placement_source(t, L._placement_source(False))
    a, b = s.index('proc cland_group_insts {prefix}'), s.index('proc cland_occupy {')
    setup = r'''
proc blk {args} {return {i0 i1 i2}}
proc i0 {args} {return {u_core.u.u_lep.u.rid\[1\]$_DFF_P_}}
proc i1 {args} {return {u_core.u.u_lep.u.rid\[1103\]$_DFF_P_}}
proc i2 {args} {return {u_core.u.u_lep.u.rid\[1\]$_DFF_P_.child}}
set ff_blk blk
'''
    return setup + 'if {[catch {\n' + check + '\n} err]} {puts $err;exit 2}\n' + s[a:b] + '\nputs "COUNT [llength [cland_group_insts {' + RID + '}]]"\n'


def test_leaf_selector_uses_actual_placement_matcher_and_excludes_descendants():
    r = subprocess.run(['tclsh'], input=script(typ()), text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    assert 'COUNT 2' in r.stdout


def test_old_hierarchy_match_is_a_negative_control():
    # The old wrapper finds the descendant but cannot anchor the two real leaf flops.
    r = subprocess.run(['tclsh'], input=script(typ('prefix')), text=True, capture_output=True)
    assert r.returncode == 0 and 'COUNT 1' in r.stdout


def test_required_leaf_match_stays_fail_closed():
    s = script(typ()).replace(r'rid\[1\]$_DFF_P_}', r'other\[1\]$_DFF_P_}').replace(
        r'rid\[1103\]$_DFF_P_}', r'other\[1103\]$_DFF_P_}')
    r = subprocess.run(['tclsh'], input=s, text=True, capture_output=True)
    assert r.returncode == 2 and 'missing native stage group' in r.stdout


def test_no_leaf_preserves_the_existing_placement_source_bytes():
    src = L._placement_source(False)
    assert L._native_stage_placement_source({}, src) == src
    assert L._native_stage_placement_source(typ('prefix'), src) == src
    t = typ('prefix')
    del t['clock']['landing_contract']['native_stage_groups']['groups'][0]['match']
    assert L._native_stage_groups(t, []) == L._native_stage_groups(typ('prefix'), [])


def test_unknown_match_is_rejected():
    with pytest.raises(ValueError, match='match must'):
        L._native_stage_groups(typ('all'), [])
