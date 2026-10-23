#!/usr/bin/env python3
"""Source-bound whole-output fanout audit and separate core publisher construction."""
from pathlib import Path
import hashlib,json,re
ROOT=Path('/home/ubuntu/wt/qdie5-hp13-1022')
OUT=Path(__file__).resolve().parent
BASE='rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv'
OLD='qfd_tt_ctlm_dv_hp13_rrloc_native32'
SHA='22b5059010fb02abbca2bb9bce1d8773b3e372c1917d2e8ef01164d4da0cbe16'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=ROOT/BASE; text=p.read_text(); assert digest(p)==SHA
 evidence_path=OUT/'clock_units/EMB_CLOCK_EVIDENCE.json'
 e=json.loads(evidence_path.read_text()); assert e['native_source']['sha256']==SHA
 src=e['calendar_sample']['source_ff_groups']; final=e['final_outputs']
 matches=list(re.finditer(r'(?m)^(?P<attr>\(\*[^\n]*?\*\)\s*)?(?P<master>qfd_bmath_\w+) #\(\.ID\(0\)\) (?P<name>u_\d+)\((?P<pins>[^;]+)\);',text))
 cells={}; drivers={}; users={}; covered=[]
 for m in matches:
  pins=dict(re.findall(r'\.(\w+)\(([^()]+)\)',m['pins'])); output=pins.get('Q',pins.get('Y')); assert output
  cells[m['name']]={'m':m,'pins':pins,'output':output};drivers[output]=m['name'];covered.append((m.start(),m.end()))
  for pin,v in pins.items():
   if pin in ('Q','Y'):continue
   for net in re.findall(r'\bn_\d+\b',v):users.setdefault(net,set()).add(m['name'])
 rows=[]; source_nets=set(); old_q=set()
 lines=text.splitlines()
 for port,width in [('emb_start',1),('emb_token',18),('emb_position',18),('emb_user',2)]:
  sr=src['u_gi.'+port]['bit_rows']; fr=final[port]['bit_rows'];assert len(sr)==len(fr)==width
  for a,b in zip(sr,fr):
   assert a['C']=='n_3159' and b['C']=='n_3160'
   assert cells[a['instance']]['pins']['Q']==a['net']
   assert cells[b['instance']]['pins']['Q']==b['net']
   # A final HR Q may only have its declaration, defining FF, and outer assign.
   hits=[(i+1,l) for i,l in enumerate(lines) if re.search(r'\b'+b['net']+r'\b',l)]
   assert len(hits)==3,(port,b['bit'],hits)
   assert not users.get(b['net']),(port,b['bit'],'internal consumer')
   source_nets.add(a['net']);old_q.add(b['net'])
   rows.append({'port':port,'bit':a['bit'],'source':a,'old_final':b,'source_cell_consumers':sorted(users.get(a['net'],[])),'old_final_internal_consumers':[],'old_final_source_lines':[i for i,l in hits]})
 assert len(rows)==39
 # Confirm both actual external consumer paths, including the additional 19-bit
 # embedding-provider branch (not just native59's 39-bit head-prepare branch).
 native_path=ROOT/'rtl/qwen_split/qfd_native59_dv_headprep_obs1.sv'; native=native_path.read_text()
 svc_path=ROOT/'rtl/qwen_split/qfd_native59_svc_obs1.sv';svc=svc_path.read_text()
 embed_path=ROOT/'rtl/qwen_split/qfd_embedding_word_provider.sv';embed=embed_path.read_text()
 case_path=ROOT/'tools/qwen_split/dv_case.py';case=case_path.read_text()
 assert 'input wire ck,rst_n' in native and '.ck(ck),.rst_n(rst_n)' in native
 for _,sink,_ in [('emb_start','head_prepare_v',1),('emb_token','head_prepare_token',18),('emb_position','head_prepare_position',18),('emb_user','head_prepare_user',2)]:
  assert '.'+sink+'('+sink+')' in native
 assert 'always @(posedge ck or negedge rst_top)' in svc
 for line in ['hp_v<={hp_v[0],head_prepare_v};hp_u0<=head_prepare_user;hp_u1<=hp_u0;','hp_t0<=head_prepare_token;hp_t1<=hp_t0;hp_p0<=head_prepare_position;hp_p1<=hp_p0;']:
  assert line in svc
 for source,sink in [('emb_start','core_start'),('emb_token','core_token')]:
  assert "('tt_ctlm', '"+source+"', 'embed_prov', '"+sink+"')" in case
  assert '.'+sink+'('+sink+')' in embed
 assert re.search(r'input\s+wire\s+ck, rst_n',embed)
 # Trace the old publication cone. Remove protection only on cells exclusive
 # to those now-unconsumed outputs; shared HR command/landing logic stays intact.
 cone=set();todo=list(old_q)
 while todo:
  net=todo.pop()
  if net in source_nets or net not in drivers:continue
  name=drivers[net]
  if name in cone:continue
  cone.add(name)
  todo += [v for k,v in cells[name]['pins'].items() if k not in ('Q','Y') and re.fullmatch(r'n_\d+',v)]
 # Non-bmath statements (macros, assigns, top ports) are external consumers.
 stripped=text
 for m in reversed(matches):stripped=stripped[:m.start()]+stripped[m.end():]
 stripped=re.sub(r'^wire [^;]+;','',stripped,flags=re.M)
 for port in final:stripped=re.sub(r'^assign '+port+r' = [^;]+;','',stripped,flags=re.M)
 outside=set(re.findall(r'\bn_\d+\b',stripped))
 protected={name for name in cone if cells[name]['output'] in outside or users.get(cells[name]['output'],set())-cone}
 todo=list(protected)
 while todo:
  name=todo.pop()
  for pin,v in cells[name]['pins'].items():
   if pin in ('Q','Y') or v not in drivers:continue
   d=drivers[v]
   if d in cone and d not in protected:protected.add(d);todo.append(d)
 exclusive=cone-protected
 assert {r['old_final']['instance'] for r in rows}<=exclusive
 audit={'source':BASE,'source_sha256':SHA,'status':'ALL39_FINAL_Q_OUTPUT_ONLY_ALL_EXTERNAL_CONSUMERS_CORE_CLOCK_FAMILY','bits':rows,'native_consumer':{'path':str(native_path.relative_to(ROOT)),'sha256':digest(native_path),'clock':'ck','width':39,'actual_sink':'u_svc.hp_v/u0/u1/t0/t1/p0/p1; first input capture and matched second stage on ck'},'native_svc_sha256':digest(svc_path),'embedding_consumer':{'path':str(embed_path.relative_to(ROOT)),'sha256':digest(embed_path),'clock':'ck','width':19,'ports':['core_start','core_token']},'die_join_source_sha256':digest(case_path),'protected_shared_old_cone_cells':len(protected),'exclusive_old_cone_unprotected_cells':sorted(exclusive),'clock_pin_changes':0,'die_clock_relation':'PENDING explicit2pin GEN root receipt; no physical phase assumption'}
 (OUT/'FANOUT_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
 model={'kind':'distinct coherent core publisher bank','sample_edges':1,'source_clock':'ck_core','field_widths':{'valid':1,'token':18,'position':18,'user':2},'field_source':'actual39u_gi registered Qs; no RESULT/NEXT token','variants':{'MAIN':{'publisher_edges':1,'total_calendar_to_output_core_edges':2,'new_ff':39},'FB':{'publisher_edges':2,'total_calendar_to_output_core_edges':3,'new_ff':78}},'old_clock_pin_changes':0,'old_HR_consumers_removed':0,'old_output_bank':'no internal consumers; remove keep attributes only on exclusive dead publication cone, allowing ordinary synthesis elimination','source_added_loads_per_GI_bit':1,'output_actual_loads_max':2,'native_input_pipeline_edges':2,'native_descriptor_build_edges':1,'TT_to_native_transport':'actual GEN required','native_to_face_transport':'actual GEN required','physical_root_relation':'explicit die clock construction required; no guessed phase/root merge','physical_area':'new39/78 publisher FFs; dead old cone may be removed, no unmeasured area credit'}
 (OUT/'MODEL.json').write_text(json.dumps(model,indent=2)+'\n')
 generated={}
 for stages in [1,2]:
  master=OLD+'_cpub39_'+str(stages); candidate=text
  for m in reversed(matches):
   if m['name'] in exclusive and m['attr']:candidate=candidate[:m.start()]+candidate[m.start()+len(m['attr']):]
  candidate=candidate.replace('module '+OLD+'(','module '+master+'(',1)
  for port in final:candidate=re.sub(r'^assign '+port+r' = [^;]+;\n','',candidate,flags=re.M)
  expr=[]
  for port in ['emb_user','emb_position','emb_token','emb_start']:
   bits=src['u_gi.'+port]['bit_rows'];expr.extend(r['net'] for r in reversed(bits))
  inst='\n// Separate core publication bank: all39 actual GI core Qs; original FF clocks untouched.\nqfd_hp13_corepub39 #(.STAGES('+str(stages)+')) u_core_emb_publish (.ck(ck_core),.i({'+','.join(expr)+'}),.o({emb_user,emb_position,emb_token,emb_start}));\n'
  candidate=candidate.replace('endmodule',inst+'endmodule',1)
  out=ROOT/'rtl/qwen_dv/headprep13/corepub39'/f'{master}.sv';out.write_text(candidate)
  generated[str(stages)]={'master':master,'source':str(out.relative_to(ROOT)),'sha256':digest(out),'publisher_stages':stages,'gi_to_output_core_edges':stages,'calendar_to_output_core_edges':1+stages}
 (OUT/'GENERATED.json').write_text(json.dumps(generated,indent=2)+'\n')
 print('AUDIT PASS all39 internal/output +58 actual external core consumers; protected',len(protected),'dead-cone keep removals',len(exclusive))
if __name__=='__main__':main()
