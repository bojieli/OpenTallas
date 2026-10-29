"""Static native reset target must agree with the existing wavefront source."""
import copy,json,re,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import schema as S,reset_tree as RT,reset_route as RR,die_trial as DT

def plan():
 raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
 raw.setdefault('reset',{}).update(release='wavefront')
 return S.Plan(raw)

def test_native_sources_and_one_raw_load():
 p=plan();w=RT.wf_plan(p);n=RR.network(p)
 assert n['raw_loads']==[dict(part=w['root'],pin='arst_n')]
 assert sum(b['arst_n']=='rst_n' for b in n['bindings'].values())==1
 assert len(n['edges'])==len(p.parts)-1
 for part,r in w['parts'].items():
  if r['parent'] is None:continue
  parent,pin=r['source'].rsplit('.',1)
  assert n['bindings'][part]['arst_n']==n['bindings'][parent][pin]
 assert n['max_release_cycles']==w['max_release']

def test_abstract_native_outputs_and_route_are_consistent():
 p=plan();n=RR.network(p);bits={}
 for tn in p.types:
  before,stats=DT.abstract_lef(p,tn)
  after,_=DT.abstract_lef(p,tn,reset_infra=True)
  bits[tn]={}
  for pin in RR.scalar_pins(p,tn):
   assert f"PIN {pin['name']}" not in before
   assert f"PIN {pin['name']}\n    DIRECTION OUTPUT ;\n    USE SIGNAL" in after
 off,_=DT.route_netlist(p,bits,channel_nets=False)
 on,_=DT.route_netlist(p,bits,channel_nets=False,reset_infra=True)
 assert off.count('.arst_n(rst_n)')==len(p.parts)
 assert on.count('.arst_n(rst_n)')==1
 for part,b in n['bindings'].items():
  for pin,wire in b.items():assert f'.{pin}({wire})' in on

def test_refuse_non_wavefront_or_unreachable(monkeypatch):
 p=plan();p.reset['release']='pipelined'
 with pytest.raises(ValueError,match='wavefront'):RR.network(p)
 p=plan();original=RT.wf_plan
 def bad(P):
  w=copy.deepcopy(original(P));w['unreachable']=['unwired'];return w
 monkeypatch.setattr(RT,'wf_plan',bad)
 with pytest.raises(ValueError,match='unreachable'):RR.network(p)
