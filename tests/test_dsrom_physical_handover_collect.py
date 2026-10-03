import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('handover', Path(__file__).resolve().parents[1]/'tools/dsrom_physical_handover_collect.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def snapshot(kind='qframe', name='C_r2_mig'):
    s = {'observed_utc':'frozen', 'host':'ot-epyc1tb', 'files':{}, 'runs':{}}
    s['runs'][name] = {'kind':kind,'path':'retained','files':{},'final_odb_exists':True,'grt_odb_exists':True}
    return s


def put(s, field, text):
    s['runs'][next(iter(s['runs']))]['files'][field] = field
    s['files'][field] = {'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}


def row(s):
    # Complete the other qframe names with unfinished empty records.
    for name in m.FRAMES:
        s['runs'].setdefault(name, {'kind':'qframe','path':'retained','files':{},'final_odb_exists':False})
    result = m.analyse(s)
    return result['runs'][next(iter(s['runs']))]


def test_inflight_zero_drc_is_not_terminal_pass():
    s = snapshot()
    put(s,'route_log','Number of violations = 0\nCompleting 40% with 11472 violations.')
    r=row(s)
    assert r['routability_pass'] is None
    assert r['final_route_violations'] is None
    assert r['progress_violations'] == 11472


def test_routed_timing_fail_is_retained():
    s=snapshot()
    put(s,'exit_code','exit=0\n')
    put(s,'route_log','Number of violations = 0')
    put(s,'drc','')
    put(s,'signoff_exit','exit=0')
    put(s,'signoff','{"corners":{"SS":{"timing":{"setup_wns_ns":-0.2}},"FF":{"timing":{"hold_wns_ns":-0.205}}}}')
    r=row(s)
    assert r['routability_pass'] is True
    assert r['SS_FF_timing_pass'] is False
    assert r['physical_admission'] is False


@pytest.mark.parametrize('missing',['drc','exit_code','route_log'])
def test_missing_terminal_evidence_cannot_pass(missing):
    s=snapshot()
    for f,t in [('drc',''),('exit_code','exit=0'),('route_log','Number of violations = 0')]:
        if f!=missing: put(s,f,t)
    assert row(s)['routability_pass'] is not True


def test_nonempty_drc_report_refuses_routability():
    s=snapshot()
    for f,t in [('drc','violation'),('exit_code','exit=0'),('route_log','Number of violations = 0')]: put(s,f,t)
    assert row(s)['routability_pass'] is False


def test_absent_ff_not_zero():
    s=snapshot()
    put(s,'signoff','{"corners":{"SS":{"timing":{"setup_wns_ns":0.1}}}}')
    put(s,'signoff_exit','exit=0')
    assert row(s)['SS_FF_timing_pass'] is None


def test_tampered_snapshot_refuses_replay():
    s=snapshot()
    put(s,'exit_code','exit=0')
    s['files']['exit_code']['text']='exit=1'
    with pytest.raises(ValueError,match='hash'): row(s)


def test_bundled_route_pass_does_not_admit_die():
    s=snapshot('die_grt','C_local_k16')
    put(s,'exit_code','exit=0')
    put(s,'grt.log','[INFO GRT-0096] Final congestion report:\nTotal 100 90 90.0% 0 / 0 / 0')
    r=row(s)
    assert r['bundled_global_route_pass'] is True
    assert r['PDN_204W_qualified'] is False
    assert r['real_tech_pin_access_qualified'] is False
    assert r['actual_clock_wire_stages'] is None


def test_live_overflow_absence_not_empty_pass():
    s=snapshot('die_grt','C_local_k16')
    put(s,'grt.log','[INFO GRT-0102] Start extra iteration 1/30')
    assert row(s)['final_overflow'] is None
    assert row(s)['bundled_global_route_pass'] is None


def test_terminal_overflow_rejected():
    s=snapshot('die_grt','C_local_k16')
    put(s,'exit_code','exit=0')
    put(s,'grt.log','GRT-0096] Final congestion report:\nTotal 100 110 110% 3 / 5 / 8')
    assert row(s)['bundled_global_route_pass'] is False


def test_positive_timing_does_not_admit_unchecked_drvs():
    s=snapshot()
    put(s,'signoff_exit','exit=0')
    put(s,'signoff','{"corners":{"SS":{"timing":{"setup_wns_ns":0.1}},"FF":{"timing":{"hold_wns_ns":0.1}}}}')
    r=row(s)
    assert r['SS_FF_timing_pass'] is True
    assert r['full_timing_and_DRV_verdict']=='NOT_ADMITTED'


def test_watcher_waits_existing_signoff_not_launches_it():
    s=snapshot()
    put(s,'exit_code','exit=0')
    row(s)
    # Single retained run has final ODB but missing signoff: collection must continue.
    reduced=copy.deepcopy(s)
    reduced['runs']={'C_r2_mig':s['runs']['C_r2_mig']}
    result=m.analyse(s)
    result['runs']={'C_r2_mig':result['runs']['C_r2_mig']}
    assert not m.watch_finished(reduced,result)
    result['runs']['C_r2_mig']['signoff_complete']=True
    assert m.watch_finished(reduced,result)


def test_tested_frames_are_not_global_minimum_proof():
    s=snapshot()
    row(s)
    assert m.analyse(s)['minimum_frame_proved'] is False


def test_inherited_graph_does_not_cover_selected_clock_control():
    a=m.source_audit()
    assert a['field_elements']==2048 and a['cfg_macros']==14336
    assert a['clock_declared_in_real_element_ports'] is True
    assert a['clock_endpoints_in_bundled_connectivity']==0
    assert a['cfg_phase_bits_in_inherited_ctl_expression']<a['selected_cfg_phase_bits_required']
