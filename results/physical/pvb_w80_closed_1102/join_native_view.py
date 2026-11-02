from pathlib import Path
import hashlib,json,sys,re
r=Path('/srv/opentallas-scratch2/claude/codex-pvb-tt-0108');k=r/'t10_w80';v=r/'native_view_w80/ot_qwen_tp8_pv_join_t';base=next(k.glob('run/results/asap7/*/base'));sys.path.insert(0,str(r/'source/tools/die_plan'));import cores;import hard_pinreg as HP
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();mod='ot_qwen_tp8_pv_join_t';core=json.load(open(k/'core.json'));lec=json.load(open(k/'lec_own_final_w80/lec.json'));so=json.load(open(k/'clock_witness_signoff/signoff.json'));cw=json.load(open(k/'clock_witness_signoff/child_clock_witness.json'));prov=json.load(open(v/'provenance.json'));gates=json.load(open(v/'gates.json'))
assert core['module']==mod and lec['verdict']=='EQUIVALENT' and lec['counts']['proved']==lec['counts']['compare_points'] and lec['superset_vec']['all_shown'] is True
assert so['verdict']=='SIGNED' and gates['view_complete'] and gates['routed_lec']=='EQUIVALENT'
assert prov['child_clock_witness']['status']=='RETAINED'
for n,h in cw['native'].items():assert sha(base/n)==h,(n,h)
assert lec['netlist']=='/work/'+str((base/'6_final.v').relative_to(k))
ports={n:(d,1 if hi is None else hi-lo+1) for n,(d,hi,lo) in core['port_decl'].items()}
lf=cores.lef_pins(v/(mod+'.lef'),mod);lp={n:(d['dir'].lower(),d['width'] or 1) for n,d in lf.items() if d['use'] not in ('POWER','GROUND')};assert lp==ports,(set(lp)^set(ports),[(n,lp.get(n),p) for n,p in ports.items() if lp.get(n)!=p][:4])
clocks={}
for c in ['tt','ff']:
 f=v/(mod+'_'+c+'.lib');assert sha(f)==prov['child_clock_witness']['view_lib_sha256'][c]
 cell=HP.parse_lib(f)[mod];text=f.read_text();types={}
 for tm in re.finditer(r'\btype\s*\(\s*"?(\w+)"?\s*\)',text):
  body,_=HP._block(text,tm.end());wm=re.search(r'bit_width\s*:\s*(\d+)',body)
  if wm:types[tm[1]]=int(wm[1])
 buses={n:body for kind,n,body in cores._groups(text) if kind=='bus'};actual={}
 for n,d in cell.items():
  if n in lf and lf[n]['use'] in ('POWER','GROUND'):continue
  width=d['width']
  if width is None:
   bt=re.search(r'bus_type\s*:\s*"?(\w+)"?',buses[n]);assert bt and bt[1] in types
   width=types[bt[1]]
  actual[n]=(d['dir'],width)
 assert actual==ports,(c,[(n,actual.get(n),p) for n,p in ports.items() if actual.get(n)!=p][:4],set(actual)^set(ports))
 clocks[c]=cores.lib_clocks(f);assert set(clocks[c])=={'clk'}
 assert cw['corners'][c]['counts']['missing']==0 and cw['corners'][c]['counts']['refs']==15939 and cw['corners'][c]['counts']['captures']==15939
rtl={str(p.relative_to(k)):sha(p) for p in sorted((k/'rtl').rglob('*')) if p.is_file()};assert len(rtl)==16
for p in [k,v]:
 with (p/'.keep').open('a') as f:f.write('PV w80 SIGNED + own final EQ; retain full native DB/SPEF/RTL/checker/AIG and clock graph for future expanded endpoint coverage. No parent expansion asserted.\n')
rec={'status':'NATIVE_SIGNED_EQ_VIEW_EXPORTED','module':mod,'renamed_master':False,'parameters':'actual elaborated core; config/core.json preserved, no TOP_PARAMS override','signal_pin_bits':sum(w for d,w in ports.values()),'core_port_buses':len(ports),'lef_tt_ff_direction_width_join':'PASS','clock_pins_and_insertion_ps':clocks,'own_final_lec':{'record':str(k/'lec_own_final_w80/lec.json'),'sha256':sha(k/'lec_own_final_w80/lec.json'),'counts':lec['counts'],'superset_vec':lec['superset_vec'],'reset_contract':lec['reset_contract'],'native_netlist_sha256':cw['native']['6_final.v']},'native_physical':cw['native'],'clock_witness':{'record':str(k/'clock_witness_signoff/child_clock_witness.json'),'sha256':sha(k/'clock_witness_signoff/child_clock_witness.json'),'counts':{c:cw['corners'][c]['counts'] for c in ['tt','ff']},'retained':True,'hierarchical_expansion':'NOT_ASSERTED'},'view':str(v),'view_complete':True,'view_files':{p.name:sha(p) for p in sorted(v.iterdir()) if p.is_file() and p.name!='.keep'},'source_rtl':rtl,'source_constraints':{p.name:sha(p) for p in k.glob('*.sdc')},'core_json_sha256':sha(k/'core.json'),'pins_sha256':sha(k/'pins.json'),'config_sha256':sha(k/'config.mk'),'actual_source_build_commit':json.load(open(k/'PROVENANCE.json'))['provenance']['commit'],'flow_tag':'NOT_ASSERTED; current native proof/view, no fabricated release tag','tool_source_commit':'d0418b5a0','checker_sha256':sha(r/'source/tools/die_plan/lec.py'),'preserve_full_native_root':str(k),'failed_A_and_B_cases_preserved':True}
(r/'NATIVE_SOURCE_CLOCK_JOIN_w80.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({n:rec[n] for n in ['status','module','signal_pin_bits','lef_tt_ff_direction_width_join','clock_pins_and_insertion_ps','view','view_complete']},indent=2))
