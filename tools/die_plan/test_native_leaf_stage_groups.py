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
set lookup_scans 0
proc blk {args} {incr ::lookup_scans;return {i0 i1 i2}}
proc i0 {args} {return {u_core.u.u_lep.u.rid\[1\]$_DFF_P_}}
proc i1 {args} {return {u_core.u.u_lep.u.rid\[1103\]$_DFF_P_}}
proc i2 {args} {return {u_core.u.u_lep.u.rid\[1\]$_DFF_P_.child}}
set ff_blk blk
'''
    return setup + 'if {[catch {\n' + check + '\n} err]} {puts $err;exit 2}\n' + s[a:b] + '\nputs "COUNT [llength [cland_group_insts {' + RID + '}]]"\n'


def test_leaf_selector_uses_actual_placement_matcher_and_excludes_descendants():
    replay = r'puts "MEMBERS [cland_group_insts {' + RID + '}]"'
    tcl = script(typ()) + replay + '\nputs "SCANS $lookup_scans"\n'
    r = subprocess.run(['tclsh'], input=tcl, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    assert r.stdout.splitlines() == ['COUNT 2', 'MEMBERS i0 i1', 'SCANS 1']


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


def test_density_filters_physical_flops_and_prices_same_packing_footprint():
    t = typ()
    t['clock']['landing_contract']['native_stage_groups']['groups'][0]['density'] = 0.55
    s = script(t)
    extra = r'''
proc fm {cmd} {switch -- $cmd {getName {return DFFHQNx1_ASAP7_75t_R} getWidth {return 1080} getHeight {return 270} isBlock {return 0}}}
proc bm {cmd} {switch -- $cmd {getName {return BUFx2_ASAP7_75t_R} getWidth {return 216} getHeight {return 270} isBlock {return 0}}}
rename i0 old_i0
rename i1 old_i1
proc i0 {args} {if {$args eq {getMaster}} {return fm};return [old_i0]}
proc i1 {args} {if {$args eq {getMaster}} {return fm};return [old_i1]}
proc i3 {args} {if {$args eq {getMaster}} {return bm};return {u_core.u.u_lep.u.rid\[2\]$_DFF_P_}}
rename blk old_blk
proc blk {args} {return {i0 i1 i2 i3}}
'''
    s = s.replace('if {[catch {\n', extra + '\nif {[catch {\n', 1)
    source = L._native_stage_placement_source(t, L._placement_source(False))
    a, b = source.index('proc cland_band_need {'), source.index('set cland_multi_seen')
    s += '\n' + source[a:b] + '\nset ff_rh 270;set ff_sw 54;set ff_dbu 1000;set cland_done {}\n'
    s += 'puts "DENSE [cland_band_need {' + RID + '} stage:hub_rid]"\n'
    s += 'puts "LEGACY [cland_band_need {' + RID + '} stage:other]"\n'
    r = subprocess.run(['tclsh'], input=s, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    assert 'COUNT 2' in r.stdout
    assert 'DENSE 2 1.07892' in r.stdout and 'LEGACY 2 1.458' in r.stdout
    # Actual cland_put and its upfront capacity check must both use the tag density.
    assert 'if {$sp eq {}} { set sp [cland_native_sp $tag];' in source
    assert 'set sp [cland_native_sp $tag]; regexp' in source


@pytest.mark.parametrize('mode,value', [('prefix', 0.55), ('cell', 0.7), ('cell', True)])
def test_density_requires_a_bounded_explicit_leaf_group(mode, value):
    t = typ(mode)
    t['clock']['landing_contract']['native_stage_groups']['groups'][0]['density'] = value
    with pytest.raises(ValueError, match='density requires'):
        L._native_stage_groups(t, [])
