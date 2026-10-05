import gzip,json
from pathlib import Path
B=Path(__file__).resolve().parents[1]/'results/uarch/dsrom_secded_clean_checker_20261002'
def test_actual_full_dynamic_ports_and_no_state():
    for k in (256,272):
        n=json.loads(gzip.decompress((B/f'terminal_r1/K{k}/mapped.json.gz').read_bytes()))['modules']['ot_rom_secded_clean_checker']
        assert {name:len(p['bits']) for name,p in n['ports'].items()}==dict(cw=k+10,syn=9,overall=1,clean=1)
        assert all(isinstance(b,int) for p in n['ports'].values() for b in p['bits'])
        assert not any('DFF' in c['type'] or 'LATCH' in c['type'] for c in n['cells'].values())
def test_all_four_real_STA_reports_and_no_library_limit_waiver():
    for k in (256,272):
        for c in ('ss','ff'):
            s=gzip.decompress((B/f'terminal_r1/K{k}/{c}.log.gz').read_bytes()).decode()
            assert 'Error:' not in s and 'table template' not in s
            assert 'Endpoint: clean' in s and 'data arrival time' in s
            assert '(VIOLATED)' not in s.split('max slew')[-1]
def test_hold_and_service_limitations_not_promoted():
    r=json.loads((B/'review.json').read_text())
    assert r['provisional_checker_cycles']==2 and r['provisional_held_II_cycles']==2
    assert not r['cycle_or_II_reduction_adopted']
    assert not r['FF_registered_hold_closed'] and not r['SS_registered_capture_closed']
    assert not r['PG_OBS_via_clock_context_closed'] and not r['PR_launched']
    assert r['rows'][0]['FF_virtual_min_hold_slack_ps']<0
    assert r['rows'][1]['FF_virtual_min_hold_slack_ps']>0
    assert r['area_credit_claimed_mm2']==0
    assert r['retained_extra_checker_allowance_mm2']>r['measured_all_checker_cell_area_mm2']
