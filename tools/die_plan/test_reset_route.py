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


def provider_fixture():
 p=plan();w=RT.wf_plan(p);n=RR.network(p)
 part=next(part for part in p.parts if RR.scalar_pins(p,p.parts[part]['type']))
 pin=RR.scalar_pins(p,p.parts[part]['type'])[0]
 x,y=p.to_die(part,pin['xy_um'])
 source=dict(port='rst_raw_n',part=part,pin=pin['name'],net=n['bindings'][part][pin['name']],
             xy_um=[x,y],source_part_release_cycles=w['parts'][part]['release'])
 root=dict(id='root',region='st:h',rect_um=[x+10,y,x+14,y+.54],clock_node='b0',
           clock_node_xy_um=[x+10,y],clock_port='t_st_root__clk',flops=8,parent=None,root=True)
 provider=dict(form='emitted_start_stage_rows',nodes=[root],edges=[])
 return p,source,provider


def test_virtual_provider_uses_one_actual_local_registered_reset():
 import landing_contract as LC
 p,s,c=provider_fixture()
 assert RR.check_provider_root(p,s,c)['errors']==[]
 st=dict(form=LC.START_FORM,uses=[],open=[],provider=c,reset_source=s)
 p.clock['landing_network']=dict(start_tree=st)
 errors=[]
 summary,_=LC._start_tree_check(p,st,{tn:{} for tn in p.types},{},errors,None)
 assert errors==[] and summary['local_root_reset']['part']==s['part']
 assert summary['local_root_reset']['physical_qualified'] is False


@pytest.mark.parametrize('mutant',['raw_pad','wrong_net','wrong_xy','wrong_release','long_hop','no_provider'])
def test_virtual_root_source_and_reach_mutants_fail(mutant):
 p,s,c=provider_fixture()
 if mutant=='raw_pad':s['pin']='arst_n'
 if mutant=='wrong_net':s['net']='rst_n'
 if mutant=='wrong_xy':s['xy_um'][0]+=1
 if mutant=='wrong_release':s['source_part_release_cycles']+=1
 if mutant=='long_hop':c['nodes'][0]['rect_um'][0]+=500;c['nodes'][0]['rect_um'][2]+=500
 if mutant=='no_provider':c=None
 assert RR.check_provider_root(p,s,c)['errors']
