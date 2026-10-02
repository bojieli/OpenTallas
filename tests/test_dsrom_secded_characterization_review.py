import gzip,importlib.util,json,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'tools'))
import dsrom_secded_characterization_review as r
def test_complete_actual_ports_and_no_state():
    for k in (256,272):
        n=json.loads(gzip.decompress((r.OUT/f'terminal_r3/K{k}/mapped.json.gz').read_bytes()))['modules']['ot_rom_secded_dec']
        assert {name:len(p['bits']) for name,p in n['ports'].items()}=={'cw':k+10,'data':k,'corrected':1,'uncorrectable':1}
        assert all(isinstance(b,int) for p in n['ports'].values() for b in p['bits'])
        assert not any('DFF' in c['type'] or 'LATCH' in c['type'] for c in n['cells'].values())
def test_raw_terminal_reports_are_real_and_preserve_negative_limits():
    for k in (256,272):
        for c in ('ss','ff'):
            s=gzip.decompress((r.OUT/f'terminal_r3/K{k}/{c}.log.gz').read_bytes()).decode()
            assert 'Error:' not in s and 'table template' not in s
            assert 'data arrival time' in s and 'slack (VIOLATED)' in s
            assert 'time 1ps' in s and 'capacitance 1fF' in s
def test_area_floor_not_free_fit_and_delay_not_pipeline_certificate():
    d=json.loads((r.OUT/'review.json').read_text())
    assert d['mapped_total_decoder_cell_area_mm2']<d['retained_decoder_allowance_mm2']
    for v in d['rows']:
        assert v['area_credit_claimed_mm2']==0 and v['retained_budget_mm2']==v['existing_allowance_mm2']
        assert v['exceeds_two_times_setup_logic_window'] and v['SS_path_library_limit_exceeded']
        assert v['diagnostic_is_not_certified_pipeline_minimum']
    assert not d['SS_registered_capture_closed'] and not d['FF_registered_hold_closed']
def test_both_prior_tool_failures_retained():
    assert json.loads((r.OUT/'mapping_postprocess_failure_r1.json').read_text())['status']=='FAIL_POSTPROCESS_YOSYS09_CELL_JSON'
    assert json.loads((r.OUT/'timing_tool_failure_r2.json').read_text())['status']=='FAIL_TIMING_REPORT'
