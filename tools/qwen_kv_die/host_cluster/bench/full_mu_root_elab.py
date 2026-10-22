#!/usr/bin/env python3
"""Check actual selected full-host MU1 elaboration, without simulating the die."""
from pathlib import Path
import json,subprocess,sys,re,hashlib
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
sources=[x for x in (root/'tools/qwen_kv_die/host_cluster/bench/sources.txt').read_text().splitlines()if x.strip()]
sources+=[str(p.relative_to(root))for p in (root/'rtl/qwen_sys/mu_qwen_20261018').glob('*.sv')]
sources+=['physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v']
selected_top=sys.argv[3]if len(sys.argv)>3 else 'qkd_host_root_admission_mu'
if selected_top!='qkd_host_root_admission_mu':sources+=['rtl/qwen_sys/kv_host_obs_20261019/'+selected_top+'.sv','rtl/qwen_sys/kv_host_obs_20261019/qkd_host_obs_csr.sv']
sources=list(dict.fromkeys(sources));mode=sys.argv[2]if len(sys.argv)>2 else 'exact'
selected=root/'rtl/qwen_sys/mu_qwen_20261018/qkd_host_root_admission_mu.sv'
if mode!='exact':
 text=selected.read_text()
 old,new={'control_drop':('qkd_host_control_prompt_observed #(.MU(1),','qkd_host_control_prompt_observed #(.MU(0),'),'record_drop':('qkd_host_record_port_mu #(.MU(1))u_records','qkd_host_record_port_mu #(.MU(0))u_records')}[mode]
 assert text.count(old)==1
 (out/'mutant.sv').write_text(text.replace(old,new))
 sources=[str(out/'mutant.sv')if x==str(selected.relative_to(root))else x for x in sources]
(out/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
cmd=['verilator','--json-only','--json-only-output',str(out/'hierarchy.tree.json'),'-Wno-fatal','-Wno-lint','-Wno-style','--top-module',selected_top,'-GENABLE_SERVICE=1','-GENABLE_NATIVE=1','-GENABLE_TOKEN=1','-GNL=2','-GMU=1']+[str(root/p)for p in sources]
with(out/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
d=json.loads((out/'hierarchy.tree.json').read_text());modules=d['modulesp'];byaddr={x['addr']:x for x in modules}
def intval(s):
 m=re.fullmatch(r"[0-9]+'s?([hdb])([0-9a-fA-F]+)",s)
 return int(m.group(2),{'h':16,'d':10,'b':2}[m.group(1)])if m else s
rows=[]
def cells(x):
 if isinstance(x,dict):
  if x.get('type')=='CELL':yield x
  else:
   for v in x.values():yield from cells(v)
 elif isinstance(x,list):
  for y in x:yield from cells(y)
def visit(module,path):
 pars={v['name']:intval(v['valuep'][0]['name'])for v in module.get('stmtsp',[])if v.get('isParam')and v.get('valuep')and v['valuep'][0].get('type')=='CONST'}
 rows.append(dict(path=path,module=module.get('origName'),parameters=pars))
 for c in cells(module.get('stmtsp',[])):
  if c['modp']in byaddr:visit(byaddr[c['modp']],path+'.'+c['name'])
visit(modules[0],modules[0]['name'])
requirements={'qkd_host_control_prompt_observed':{'MU':1},'qkd_host_fullcontrol_observed':{'MU':1,'NSLOT':4,'PLB':11},'qkd_host_if_pins_observed':{'NSLOT':4,'ENG_CTX':4,'MU_OUT':1,'PLB':11},'ot_host_if_pb2_observed':{'NSLOT':4,'ENG_CTX':4,'MU_OUT':1,'PLB':11},'qkd_host_record_port_mu':{'MU':1},'qkd_host_native_context_tx_mu':{},'qkd_host_tp8_coordinator_mu':{'MU':1,'POST_UID_SLOT':1},'qkd_host_post_collector_mu':{'MU':1,'UID_SLOT':1}}
selected_rows=[x for x in rows if x['module']in requirements];errors=[]
for mod,params in requirements.items():
 found=[x for x in selected_rows if x['module']==mod]
 if not found:errors.append('absent '+mod)
 for row in found:
  for k,v in params.items():
   if row['parameters'].get(k)!=v:errors.append(row['path']+'.'+k+'='+str(row['parameters'].get(k))+' expected'+str(v))
result=dict(passed=not errors,mode=mode,root_source_sha256=hashlib.sha256(selected.read_bytes()).hexdigest(),top=selected_top,top_params=dict(MU=1,ENABLE_SERVICE=1,ENABLE_NATIVE=1,ENABLE_TOKEN=1,NL=2),selected_hierarchy=selected_rows,errors=errors)
(out/'selected_hierarchy.json').write_text(json.dumps(result,indent=2)+'\n')
print('FULL_MU_ROOT_CONTRACT '+('PASS'if not errors else'FAIL')+' mode='+mode+' '+str(errors),flush=True)
raise SystemExit(bool(errors))
