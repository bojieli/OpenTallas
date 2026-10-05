import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_named_pg_escape as P
@pytest.fixture(scope='module')
def facts():
 d=P.B.C.inputs();hd,_=P.B.C.H.H.inputs()
 return P.tech(),hd['cell_LEF.json']['BUFx4_ASAP7_75t_R'],d
@pytest.mark.parametrize('orientation',['R0','MX'])
@pytest.mark.parametrize('pin',['A','Y'])
def test_buffer_literal_pin_escape(facts,orientation,pin):
 g,lef,d=facts;c=dict(d['selector_core_clock_cells.jsonl.gz'][0]);c['orientation']=orientation
 r=P.local_escape(c,pin,g,lef)
 assert r['M1_literal_landing_contained'] and r['actual_net_assignment'] is None
 assert len(r['shapes'])==7
 assert {s['layer'] for s in r['shapes']}=={'M1','M2','M3','V1','V2'}
 assert r['port_route_above_M3_not_bound']
def test_bank_feed_uses_existing_gap_and_named_rails(facts):
 g,lef,d=facts;b=d['model.json']['selector_additional_core_clock_bank'];r=P.pg_feed('bank',b['named_site_bank_bbox_DBU'],b['PG_M1_literal_rails'],g,b['source_current_selector_bbox_DBU'][2])
 assert r['local_rail_taps']==2937
 assert r['VIA12_instances']==r['VIA23_instances']==2937
 assert r['upstream_supply_current_EM_voltage_drop'] is None
 assert r['proposed_left_extent_DBU']>=b['source_current_selector_bbox_DBU'][2]
def test_no_zero_gap_pg_borrow(facts):
 g,lef,d=facts;b=d['model.json']['selector_additional_core_clock_bank']
 with pytest.raises(ValueError,match='gap'):P.pg_feed('bad',b['named_site_bank_bbox_DBU'],b['PG_M1_literal_rails'],g,b['named_site_bank_bbox_DBU'][0])
