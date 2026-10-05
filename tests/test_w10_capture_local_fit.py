import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w10_capture_local_fit as C
RECORD=ROOT/'results/uarch/w10_baseline_wake/local_fit_r1/audit.json'

def test_capture_muxes_do_not_fit_ff_only_pin_band():
    #20-site flop alone hides actual 6+6-site capture mux feedback gates.
    assert C.row_pack([20]*142,120)<=51
    assert C.row_pack([32]*142+[5]*16,120)==142
    assert C.row_pack([32]*142+[5]*16,192)<=51
    assert C.row_pack([32]*142+[5]*16,190)>51

def test_actual_macro_capture_accounting_and_orientation():
    x=json.loads(RECORD.read_text());g=x['edge_budgets']
    assert sum(r['capture_bits'] for r in g)==x['capture_flops']==1088
    assert all(r['capture_bits']==(130 if r['edge']=='west' else 142) for r in g)
    assert all(r['actual_capture_pin_band_rows']==(47 if r['edge']=='west' else 52) for r in g)
    assert all(r['bundle_sites']==[32] and not r['corridor_120sites_pin_band_fits'] for r in g)
    assert all(r['corridor_120sites_rows']<=x['macro_side_rows'] for r in g)
    assert all(r['physical_edge']!=r['edge'] for r in g if 'g_mac[1]' in r['macro'])

def test_icg_load_is_not_qualified_by_eight_distinct_enables():
    x=json.loads(RECORD.read_text());g=x['icg_gates']
    assert [r['flop_clock_sinks'] for r in g]==[10108,6161,5269,67762,0,0,0,0]
    assert sum(r['flop_clock_sinks'] for r in g)+2433==91733
    assert all(r['unbuffered_endpoint_load_exceeds_ICG_max_capacitance'] for r in g[:4])
    assert all(not r['unbuffered_endpoint_load_exceeds_ICG_max_capacitance'] for r in g[4:])
    assert all(r['macro_CLK_capacitance_ff']==8.6838 for r in g[4:])
    assert not x['physical_admission'] and x['jobs_launched']==0
    assert '155.103.253.39' in x['physical_admission_excluded_hosts']

def test_source_mutant_fails_before_cone_claim(tmp_path):
    p=tmp_path/'mutant.v';p.write_text('module smaller; endmodule')
    with pytest.raises(AssertionError):C.audit(p,p,p,p)

def test_liberty_block_parser_keeps_nested_scopes():
    s='cell (A) { pin (CLK) { capacitance : 1; timing () { x : 2; } } } cell (B) {}'
    b=C.block(s,r'cell\s*\(A\)');assert 'cell (B)' not in b and 'timing' in b
    assert C.block(b,r'pin\s*\(CLK\)').endswith('}')

def test_named_construction_has_no_local_overlap_or_density_borrowing():
    x=json.loads(RECORD.read_text());seen_ff=set()
    for edge in x['row_bin_certificates']:
        assert len(edge['rows'])<=edge['available_rows']
        seen=set()
        for row in edge['rows']:
            end=0
            for c in row['cells']:
                assert c['name'] not in seen;seen.add(c['name'])
                assert c['site_start']==end
                end+=c['site_width']
                if c['type'].startswith('DFF'):
                    assert c['name'] not in seen_ff;seen_ff.add(c['name'])
            assert end==row['used']<=edge['width_sites']//2
    assert len(seen_ff)==1088
