from pathlib import Path
import json,hashlib,importlib.util,os,time
p=Path('/out');e=json.loads((p/'EXPECTED.json').read_text());assert e['subject']=='/srv/opentallas-scratch2/claude/codex-kv-ahub-fault-full-2055' and e['rtl_files']==47
for f,h in e['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
assert e['old_source_sha256']=='dbff40e4b29d0fa1a81ec75167557dce3dbb9a06194c3c5eab77c99ce216a14b'
assert hashlib.sha256(Path('/work/rtl/qkd_ahub_static_dw.sv').read_bytes()).hexdigest()==e['new_source_sha256']
(p/'INPUTS_ASSERTED.json').write_text(json.dumps(dict(e,asserted_before_frontend=True),indent=2)+'\n')
s=importlib.util.spec_from_file_location('F',p/'lec.py');F=importlib.util.module_from_spec(s);s.loader.exec_module(F);logs=[];t=time.time()
F.run_yosys((p/'gold.ys').read_text(),p/'gold.ys',logs)
L=F.Lec(F.read_aig(p/'gold.aig'),F.read_map(p/'gold.map'),F.read_aig('/subject/proof/normal/gate.aig'),F.read_map('/subject/proof/normal/gate.map'));L.kit_reset_ports=['rst_n']
F.normalize_gold_elements(L,F.slang_elements(p/'gold.aliases.json'),logs);F.json_alias_keys(L,logs,work=p);F.slang_element_keys(L,logs,work=p);F.alias_arrays(L,logs,work=p)
point='ff:u_dut.u_leaf.u_core.fault';vals={};base={}
for side,d,points in [('gold',L.gold,L.gp),('gate',L.gate,L.tp)]:
 assert point in points
 levels={};R=F.reset_vars(d,points,asserted={'pi:rst_n[0]':0},levels=levels,declared=['rst_n']);assert levels=={'pi:rst_n[0]':0}
 st,first=F.reset_state(d,R,16);lit=points[point];v=st.get(lit>>1);vals[side]=None if v is None else v^(lit&1)
 base[side]={'asserted_resets':levels,'value':vals[side],'became_constant_edge':first.get(lit>>1),'literal':lit}
assert vals=={'gold':1,'gate':0},vals
r={'classification':'DECISIVE_ACTUAL_SOURCE_RESET_NEGATIVE','negative_control':'REJECTED_WITH_NATIVE_RESET_WITNESS','point':point,'witness':base,'reset_edges':16,'other_primary_inputs':'arbitrary/unknown; no guessed values or correspondence hypotheses','hypotheses':0,'constraints':0,'source':e,'native_graph_sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['gold.aig','gold.map']},'elapsed_s':time.time()-t,'scope':'Only actual mutated gold frontend rebuilt. Exact original mapped gate AIG reused. Native reset fault comparison only; no full compare/discovery/SYNTH/physical.'}
(p/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n');(p/'NATIVE.log').write_text('\n'.join(logs));print('RESET_NEGATIVE_WITNESS',vals,flush=True)
