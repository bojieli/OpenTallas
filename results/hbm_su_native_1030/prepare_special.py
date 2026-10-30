"""Source-only adapter for the four actual packed44 native SU cuts."""
import copy,json,pathlib,re,sys
from pin_plan import PACK,ROOT,ports
from boundary_graph import adapter,topology
HERE=pathlib.Path(__file__).parent;BASE=ROOT/'physical/die_plan/hbm_arch_cores';top='ot_hnx_su_plain4__7dd6a1bbbf47_rst3';physical=top+'__id44';P=ports(top)
assert dict((n,w)for d,n,w in P)['lane_lane_id']==44
text='`timescale 1ns/1ps\n`default_nettype none\n// SOURCE PREP: actual native packed four independent11bit lane IDs; R7 bypass proof still required.\nmodule '+physical+'(\n'+',\n'.join(' '+d+' wire '+(f'[{w-1}:0] 'if w>1 else'')+('strap_lane_lane_id'if n=='lane_lane_id'else n)for d,n,w in P)+'\n);\n '+top+' u_native(\n'+',\n'.join('  .'+n+'('+('strap_lane_lane_id'if n=='lane_lane_id'else n)+')'for d,n,w in P)+'\n );\nendmodule\n`default_nettype wire\n'
(BASE/'wrappers'/(physical+'.sv')).write_text(text);A=adapter(physical,top);T=topology(top)
raw=(PACK/(top+'.sv')).read_text();id_graph=[]
for bank in range(4):
 body=re.search(r'\bm'+str(2*bank+1)+r'\s*\((.*?)\);',raw,re.S).group(1)
 bits=list(reversed([v.strip() for v in re.search(r'\.lane_id\(\{(.*?)\}\)',body).group(1).split(',')]))
 assert bits==['lane_lane_id['+str(11*bank+j)+']'for j in range(11)]
 id_graph.append(dict(member='m'+str(2*bank+1),port='lane_id',native_top_bits_lsb_first=bits))
facts=[r for r in json.load(open(HERE/'native_cut_abi.json'))if r['module']==top];assert len(facts)==4
sys.path.insert(0,str(ROOT/'tools/die_plan'));from parent_id_straps import validate_parent_id_straps
rows=[];mutants=0
for r in facts:
 v=r['ids']['lane_lane_id']['value'];lanes=[(v>>(11*i))&2047for i in range(4)];assert lanes in([40,41,42,43],[56,57,58,59])
 d=dict(module=physical,inst=r['local'],straps=[dict(port='strap_lane_lane_id',width=44,value=v)],physical_id_alias={'strap_lane_lane_id':'lane_lane_id'},packed_lane_id_contract=dict(kind='SU_PACKED_LANE_IDS_4X11',lanes=lanes))
 assert validate_parent_id_straps(d,inputs={'strap_lane_lane_id':44},actual_module=physical)=={'strap_lane_lane_id':{'width':44,'value':v}}
 for mutation in ['wrongwidth','wrongmaster','wrongactualmaster','wrongpack','wronglanes','undeclared']:
  bad=copy.deepcopy(d);actual=physical
  if mutation=='wrongwidth':bad['straps'][0]['width']=9
  elif mutation=='wrongmaster':bad['module']='unapproved_similar_master'
  elif mutation=='wrongactualmaster':actual='other_hardware'
  elif mutation=='wrongpack':bad['straps'][0]['value']^=1
  elif mutation=='wronglanes':bad['packed_lane_id_contract']['lanes'][0]^=1
  elif mutation=='undeclared':bad.pop('packed_lane_id_contract')
  try:validate_parent_id_straps(bad,inputs={'strap_lane_lane_id':44},actual_module=actual)
  except ValueError:mutants+=1
  else:raise AssertionError('escaped '+mutation)
 rows.append(dict(native_path=r['path'],part=r['part'],local=r['local'],native_packed_value=v,lanes_lsb_first=lanes,descriptor_PREP=d))
try:adapter(physical,top,True)
except AssertionError:mutants+=1
else:raise AssertionError('wrong-ID wiring escaped')
manifest=json.load(open(HERE/'su_source_manifest.json'));regular='ot_hnx_su_plain4__lid9_rst3'
assert set(manifest['roots'][top])-{top}==set(manifest['roots'][regular])-{regular}
R=json.load(open(BASE/'recipes_b2.json'));rec=copy.deepcopy(R['ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77']);rec['top']=top;rec['files']=[p.replace('ot_hnx_su_plain4__lid9_rst3__synth.sv',top+'__synth.sv')for p in rec['files']];rec.pop('macro_placement',None);rec['source']='SOURCE PREP ONLY: exact four actual native special packed44-ID cuts. Same34-module preferred closure/native7defines. No regular9bit alias, no physical slot/outline/PNR adoption. Native packed ID capture still HOLD until R7 bypass qualification.';R[physical]=rec;(BASE/'recipes_b2.json').write_text(json.dumps(R,indent=1)+'\n')
(HERE/'special_adapter_receipt.json').write_text(json.dumps(dict(status='PASS_SOURCE_ADAPTER_AND_TYPED_CONTRACT_ONLY',adapter=A,output_graph=T,independent_identity_graph=id_graph,actual_four_bindings=rows,negative_controls_rejected=mutants,hold='No physical pinplan/slot adoption; native R7 ID capture remains until actual sequence proof and variant intake'),indent=1)+'\n');print('PASS4special cuts16independent11bitIDs',mutants,'negative controls')
