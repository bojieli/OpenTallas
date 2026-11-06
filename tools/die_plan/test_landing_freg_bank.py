"""Separate physical first-capture bank preserves ordinary ring placement."""
import pytest
import landing_place as L


def fixture():
    t = {'outline_um': [1442.88, 1226.88], 'clock': {'landing_ring_wreg':
         {'buses': ['ft2_i'], 'freg': True, 'dsrep': 8}}}
    b = {'ring_place': 'ff', 'rect_um': [17.28, 935.82, 128.22, 961.74]}
    return t, b


def test_default_groups_unchanged():
    t, b = fixture()
    assert L._band_groups('T', 'ft2_i', b, t) == [
        ('u_cland_ft2_i', b['rect_um'], 'ring:ft2_i+ff')]


def test_first_capture_precedes_storage_with_unique_tag():
    t, b = fixture()
    b['freg_rect_um'] = [6.48, 1211.76, 117.72, 1221.48]
    g = L._band_groups('T', 'ft2_i', b, t)
    assert g[0] == ('u_cland_ft2_i.g_freg.u_face', b['freg_rect_um'], 'ring:ft2_i@freg+ff')
    assert g[1] == ('u_cland_ft2_i', b['rect_um'], 'ring:ft2_i+ff')
    assert g[0][2] != g[1][2]


@pytest.mark.parametrize('rect', [[0, 0, 1, float('inf')], [0, 0, 1500, 2], [20, 940, 120, 950]])
def test_bad_or_overlapping_face_rejected(rect):
    t, b = fixture(); b['freg_rect_um'] = rect
    with pytest.raises(ValueError): L._band_groups('T', 'ft2_i', b, t)


def test_no_silent_register_insertion():
    t, b = fixture(); b['freg_rect_um'] = [6, 1210, 118, 1222]
    t['clock']['landing_ring_wreg']['freg'] = False
    with pytest.raises(ValueError, match='requires this bus FREG'):
        L._band_groups('T', 'ft2_i', b, t)


def test_actual_instance_lookup_separates_first_capture_from_storage():
    import subprocess
    from pathlib import Path
    text = Path(L.__file__).with_name('landing_placement.tcl').read_text()
    helper = text[text.index('proc cland_group_insts {prefix}'):text.index('proc cland_occupy')]
    script = r"""
set ff_blk blk
set names {u_bound.u_cland_ft2_i.g_freg.u_face/q[0] u_bound.u_cland_ft2_i.g_freg.u_face/q[514] u_bound.u_cland_ft2_i/u_ring.s_d[0][0] u_bound.u_cland_ft20_i.g_freg.u_face/q[0]}
proc blk {method} {global names;return $names}
foreach name $names {proc $name {method} [list return $name]}
""" + helper + r"""
set face [cland_group_insts u_cland_ft2_i.g_freg.u_face]
if {[llength $face] != 2} {error "wrong first capture inventory: $face"}
set cland_done {}
foreach i $face {dict set cland_done [$i getName] 1}
set rest {}
foreach i [cland_group_insts u_cland_ft2_i] {
 if {![dict exists $cland_done [$i getName]]} {lappend rest [$i getName]}
}
if {[llength $rest] != 1 || ![string match *u_ring.s_d* [lindex $rest 0]]} {
 error "first captures would be moved again: $rest"
}
puts "SEPARATE_CAPTURE_PASS"
"""
    r = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert r.returncode == 0 and 'SEPARATE_CAPTURE_PASS' in r.stdout, (r.stdout, r.stderr)
    assert not r.stderr
