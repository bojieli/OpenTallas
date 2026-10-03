import importlib.util,json
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('current',Path(__file__).resolve().parents[1]/'tools/dsrom_current_die_feasibility.py');C=importlib.util.module_from_spec(s);s.loader.exec_module(C)

def test_full_clock_control_and_cfg_source_identity():
 C.D.CTL=C.CTL;g=C.geometry();i,n=C.graph(g)
 m=C.model();assert m['PHW']==10 and m['control_bits']==16
 assert m['clock_cfg_endpoints']==14336 and m['clock_element_endpoints']==2048
 assert m['compiled_weight_macros']==8192 and m['full_die_admitted'] is False
 for e in n:
  if e.cls=='cfg_macro_to_wordmux' and e.id.endswith('_d'):
   cfg=next(c for c in g['cfgs'] if c.name==e.src[0]);pair=cfg.meta['pair']
   dest=next(x for x in n if x.cls=='cfg_word_to_element' and x.id==f'e{pair}_cfg')
   assert e.dsts[0][0]==dest.src[0]

def test_R49_c9_no_annex_no_recharge():
 g=C.geometry();b={i.name:i for i in g['blocks']}
 assert 'CAPTURE_HOME' not in b
 assert b['CAPTURE_RAW'].w==pytest.approx(204.93)
 assert b['CAPTURE_COMMON'].x==pytest.approx(11188.476)
 assert b['SELECTOR_CLOCK_BANK'].x==pytest.approx(3129.786)
 assert len([i for i in b if 'CLOCK_BANK' in i])==1

def test_no_crossdie_raw_capture_mux():
 for shard,seats in [(0,320),(1,256)]:
  g=C.geometry(shard=shard);assert g['shard']==shard
  assert C.load(C.R49)['per_shard_raw_homes'][shard]['seats']==seats
  i,n=C.graph(g)
  assert all(e.dsts==[('CAPTURE_RAW',e.id[:-3])] for e in n if e.cls=='return_to_vm')

def test_v1_macro_and_positive_wire_screen():
 m=C.model();assert m['v1_cfg_abstract']==C.CFGLEF
 assert m['actual_full_token_added_cycles'] is None
 assert all(e['wire_pipeline_lower_screen_cycles']>=1 for e in m['edges'].values() if not e['class'].startswith(('clock','reset')))

def test_native_pin_cases_have_real_macro_and_positive_pin_count(tmp_path):
 cases=C.prepare_pin(tmp_path/'pin','D',0)
 assert all(c['signal_pins']>0 for c in cases)
 assert cases[-1]['abstract_scope']=='actual v1 macro'
 assert 'pin_access' in (tmp_path/'pin/cfg.tcl').read_text()
 assert '-bottom_routing_layer' not in (tmp_path/'pin/cfg.tcl').read_text()
 assert 'set_routing_layers -signal M1-M9' in (tmp_path/'pin/cfg.tcl').read_text()

def test_PDN204_power_conserved_and_mesh_debit(tmp_path):
 r=C.prepare_pdn(tmp_path/'pdn','D',0)
 assert r['total_W']==pytest.approx(204)
 assert r['M8_M9_each_PG_fraction']==pytest.approx(16/90)
 assert r['full_die_PG_admitted'] is False
 powers=json.loads((tmp_path/'pdn/power_map.json').read_text())
 assert sum(powers.values())==pytest.approx(204)
 assert all(p>0 for p in powers.values())
 assert r['mesh_width_um']<=r['native_max_width_um']
 assert r['actual_mesh_fraction']<=r['M8_M9_each_PG_fraction']
 assert r['mesh_pitch_um']/.08==pytest.approx(round(r['mesh_pitch_um']/.08))
