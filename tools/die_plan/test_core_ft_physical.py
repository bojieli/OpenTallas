from pathlib import Path
import copy,hashlib,json,sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'));sys.path.insert(0,str(ROOT/'tools/autopilot'))
import core_ft_physical as F
import prov_view as PV
R=ROOT/'physical/die_plan/qwen_compute/ft_physical_1106'

def case(short):
 d=R/short;r=json.loads((d/'proof.json').read_text());m=r['module'];decl=json.loads((d/'ft_ports.json').read_text());inputs=[p['name'] for p in decl['ports'] if p['direction']=='INPUT'];outputs=[p['name'] for p in decl['ports'] if p['direction']=='OUTPUT']
 e={'module':m,'outline_um':r['outline_um'],'pins_file':str(d/'plan_pins.json'),'physical_ft':{'proof':str(d/'proof.json'),'proof_sha256':F.sha(d/'proof.json'),'unconsumed_outputs':outputs},'native_port_adapter':{'merge':{},'cycles':0,'tie':{n:"1'b0" for n in inputs}}};return d,m,e

@pytest.mark.parametrize('short',['vmr','crh'])
def test_actual_qualified_view_full_pin_match_and_explicit_header(short):
 d,m,e=case(short);c=F.load(e,m,d/(m+'.lef'),d/(m+'_tt.lib'),d/(m+'_ff.lib'),ppins=json.loads((d/'plan_pins.json').read_text()));h=(d/'core_header.txt').read_text();new=F.extend_header(h,c)
 assert all(p['name'] in new for p in c['ports'])
 corepins=PV.plan_pins(e,str(d));assert PV.check_routed(str(d),m,e,corepins,None,str(ROOT))==(True,'ok')
 assert [x['kind'] for x in c['isolation']]==['clock','reset']
 assert sum(len(x['cells']) for x in c['isolation'])==2

@pytest.mark.parametrize('short',['vmr','crh'])
def test_actual_cone_mutant_reaching_core_clock_is_refused(short):
 d,m,e=case(short);text=F.read_text(d/'route.v.gz');decl=json.loads((d/'ft_ports.json').read_text());mut=text.replace('endmodule'," DFFHQNx1_ASAP7_75t_R MUTANT (.CLK(ft_ck_i), .D(ck), .QN(fault));\nendmodule",1)
 with pytest.raises(ValueError,match='non-unary/core'):F.isolation(mut,m,decl,F.unary_cells(d/'primitive.lib.gz'))

@pytest.mark.parametrize('short',['vmr','crh'])
def test_compound_side_effect_mutant_is_refused(short):
 d,m,e=case(short);text=F.read_text(d/'route.v.gz');decl=json.loads((d/'ft_ports.json').read_text());mut=text.replace('endmodule',' assign fault = ft_ck_i | ck;\nendmodule',1)
 with pytest.raises(ValueError,match='compound expression'):F.isolation(mut,m,decl,F.unary_cells(d/'primitive.lib.gz'))

@pytest.mark.parametrize('field',['tie','outputs','module','header','pin'])
def test_declared_contract_mutants_fail_closed(field,tmp_path):
 d,m,e=case('vmr');pins=json.loads((d/'plan_pins.json').read_text());h=(d/'core_header.txt').read_text()
 if field=='tie':e['native_port_adapter']['tie']['ft_ck_i']="1'b1"
 if field=='outputs':e['physical_ft']['unconsumed_outputs']=[]
 if field=='module':m='other_core'
 if field=='pin':
  if isinstance(pins,list):pins[0]['x']+=1
  else:pins['pins'][0]['x']+=1
 if field=='header':
  c=F.load(e,m,d/(m+'.lef'),d/(m+'_tt.lib'),d/(m+'_ff.lib'),ppins=pins)
  with pytest.raises(ValueError,match='logical core header'):F.extend_header(h.replace('fault','WRONG_FAULT'),c)
 else:
  with pytest.raises(ValueError):F.load(e,m,d/(e['module']+'.lef'),d/(e['module']+'_tt.lib'),d/(e['module']+'_ff.lib'),ppins=pins)

def test_selected_view_hash_mutant_is_refused(tmp_path):
 d,m,e=case('vmr');bad=tmp_path/'bad.lib';bad.write_bytes((d/(m+'_tt.lib')).read_bytes()+b'\n/* mutant */')
 with pytest.raises(ValueError,match='selected tt'):F.load(e,m,d/(m+'.lef'),bad,d/(m+'_ff.lib'),ppins=json.loads((d/'plan_pins.json').read_text()))
