"""Existing OWNER10-28 R8 straps need declared physical sites under count_straps."""
import copy,json
from pathlib import Path
import schema as S
import gen_phys as G
from test_landing_pin_inventory import vehicle
import port_bind_gate as B

def test_r8_count_strap_schema_accepts_only_approved_names():
 raw=json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text());tn=next(iter(raw['partition_types']))
 raw['partition_types'][tn]['count_straps']=[dict(name='strap_r8pad_core_red_addr',width=4,layer='M5',sites_um=[[3+i*4.32,7] for i in range(4)])]
 assert S.validate(raw)==[]
 rogue=copy.deepcopy(raw);rogue['partition_types'][tn]['count_straps'][0]['name']='strap_rogue_count'
 assert S.validate(rogue)

def test_r8_physical_count_pins_are_exact_not_prefix_exempt(monkeypatch):
 p=vehicle();p.types['t']['count_straps']=[dict(name='strap_r8pad_core_red_addr',width=4,layer='M5',sites_um=[[3+i*4.32,7] for i in range(4)])]
 monkeypatch.setattr(G,'tap_pins',lambda *_:[]);monkeypatch.setattr(G,'reset_out_pins',lambda *_:[])
 pins=G.port_bind_pin_records(p,'t',[])
 text='module top(strap_r8pad_core_red_addr,fclk_in_x,fclk_out_x,cland_up_ready_x);\ninput [3:0] strap_r8pad_core_red_addr;\ninput fclk_in_x;\noutput fclk_out_x;\noutput cland_up_ready_x;\nendmodule\n'
 assert B.check(text,'top',pins,['strap_r8pad_core_red_addr'])['verdict']=='PASS'
 old=[r for r in pins if not r['bus'].startswith('strap_r8pad_')]
 assert B.check(text,'top',old)['extra']==4
 rogue=text.replace('output fclk_out_x;','input strap_r8pad_rogue;\noutput fclk_out_x;')
 assert B.check(rogue,'top',pins,['strap_r8pad_core_red_addr'])['extra']==1
