"""Plain G2 must not promote zero-overflow results without actual-site proof."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g2


def vehicle(tmp, second=400):
    (tmp/'io.tcl').write_text('place_pin -pin_name {ft0_i[0]} -layer M6 -location {0 0}\n'
        'place_pin -pin_name {ft0_o[0]} -layer M6 -location {800 0}\n')
    (tmp/'probe.tcl').write_text('place_inst -name st_ft0_0_0 -location {4 0}\n'
        'place_inst -name st_ft0_0_1 -location {400 0}\n')
    (tmp/'insts.tsv').write_text('st_ft0_0_0\tDFFHQNx1_ASAP7_75t_R\t4\t0\t5.08\t.27\n'
        f'st_ft0_0_1\tDFFHQNx1_ASAP7_75t_R\t{second}\t0\t{second+1.08}\t.27\n')
    return dict(kind='g2-partition',done=True,total_overflow=0,errors=[],pin_access_no_ap={})


def test_actual_dpl_movement_controls_plain_g2_pass(tmp_path):
    r=vehicle(tmp_path,410)
    g2.attach_actual_geometry(tmp_path,r)
    assert r['ft_hops']['max_hop_um']==406 and r['geometry_verdict']=='FAIL'
    assert not g2.probe_passes(r)
    # Mutant drops the physical movement; the otherwise identical zero-overflow
    # result would pass on the old planned coordinates.
    r=vehicle(tmp_path,400);g2.attach_actual_geometry(tmp_path,r)
    assert r['geometry_verdict']=='PASS' and g2.probe_passes(r)


def test_no_actual_dump_or_cached_proof_fails_closed(tmp_path):
    r=vehicle(tmp_path);(tmp_path/'insts.tsv').unlink()
    g2.attach_actual_geometry(tmp_path,r)
    assert not g2.probe_passes(r) and r['geometry_verdict']=='FAIL'
    cached=dict(kind='g2-partition',done=True,total_overflow=0,errors=[],pin_access_no_ap={})
    assert not g2.probe_passes(cached)
    cached['kind']='g2-die'
    assert g2.probe_passes(cached)
    cached['errors']=['GRT-ERROR']
    assert not g2.probe_passes(cached)


def test_explicit_packed_anchors_must_not_be_replaced_by_legalizer_sites(tmp_path):
    r=vehicle(tmp_path,405)
    (tmp_path/'station_sites.json').write_text(json.dumps({'st_ft0_0_1':[400.,0.]}))
    g2.attach_actual_geometry(tmp_path,r)
    assert not r['ft_hops']['over_reach']  # Reach itself remains legal.
    assert r['ft_hops']['explicit_anchor_drift_um']==5
    assert not g2.probe_passes(r) and 'moved or missing' in ';'.join(r['ft_hops']['errors'])
