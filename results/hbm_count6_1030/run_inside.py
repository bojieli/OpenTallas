#!/usr/bin/env python3
import collections,json,pathlib,re,subprocess,sys
K=pathlib.Path('/work');S=json.load(open(K/'source.json'));result=dict(instance=S['instance'],module=S['module'],params=S['params'],defines=S['defines'],scope='Actual current native WHOLE wrapper, direct wiring0addedFF; no PNR/LEC; realqualifiedmemoryproviders only',source_hashes=S['source_hashes'])
def finish(status,reason=None,rc=0):
 result.update(status=status,reason=reason);(K/'count_result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='source_hashes'}),flush=True);raise SystemExit(rc)
with open(K/'pre.log','w')as f:r=subprocess.run(['yosys','-Q','-T','-s','/work/pre.ys'],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:finish('BLOCKED_SOURCE_OR_HARDWARE','Native preferred-source elaboration failed; see pre.log',r.returncode)
J=json.load(open(K/'pre.json'));mods=J['modules'];root=mods[S['top']];child=mods[root['cells']['u_current']['type']]
actual={n:dict(direction=v['direction'],width=len(v['bits']))for n,v in child['ports'].items()}
if actual!=S['ports']:result['actual_ports']=actual;finish('BLOCKED_NATIVE_ABI_MISMATCH','Actual explicit parameters/source port inventory differs from current469 binding',2)
allowed=set(S['macro_allowlist'])
for n,m in mods.items():
 if m.get('attributes',{}).get('blackbox') not in (None,'0','00000000000000000000000000000000',0):
  if n not in allowed:finish('BLOCKED_UNQUALIFIED_BLACKBOX','No fake hardchild blackbox permitted: '+n,3)
def number(v):return int(v,2)if isinstance(v,str)else int(v)
def inventory(name,stack=()):
 if name in stack:raise RuntimeError('recursive nativehierarchy')
 if name in allowed:return (0,collections.Counter({name:1}))
 m=mods[name];bits=0;counts=collections.Counter()
 for c in m.get('cells',{}).values():
  if c['type']=='$mem_v2':bits+=number(c['parameters']['WIDTH'])*number(c['parameters']['SIZE'])
  elif c['type']in mods:
   cb,cc=inventory(c['type'],stack+(name,));bits+=cb;counts.update(cc)
 return bits,counts
bits,macro_pre=inventory(S['top']);result.update(native_inferred_memory_bits=bits,actual_pre_macro_instances=dict(macro_pre));cap=max(4096,bits)
with open(K/'config.mk','a')as f:f.write('export SYNTH_MEMORY_MAX_BITS = '+str(cap)+'\n')
with open(K/'synth.log','w')as f:r=subprocess.run(['make','DESIGN_CONFIG=/work/config.mk','WORK_HOME=/work/run','FLOW_VARIANT=base','NUM_CORES=8','synth'],cwd='/OpenROAD-flow-scripts/flow',stdout=f,stderr=subprocess.STDOUT)
if r.returncode:finish('BLOCKED_SYNTH_FAILURE','Whole native mapping failed; preserve synth.log',r.returncode)
reports=list(K.glob('run/logs/asap7/*/base/1_synth.json'))
if len(reports)!=1:finish('BLOCKED_MISSING_MAPPED_COUNT','No unique official mapped synthesis metrics',4)
j=json.load(open(reports[0]));keys={'mapped_std_cells':'synth__design__instance__count__stdcell','mapped_macro_cells':'synth__design__instance__count__macros','mapped_total_cells':'synth__design__instance__count','std_area_um2':'synth__design__instance__area__stdcell','macro_area_um2':'synth__design__instance__area__macros'}
for dst,src in keys.items():
 if src not in j:finish('BLOCKED_MISSING_MAPPED_COUNT','Official metrics missing '+src,5)
 result[dst]=j[src]
net=next(K.glob('run/results/asap7/*/base/1_2_yosys.v'),None)
if net is None:net=next(K.glob('run/results/asap7/*/base/1_synth.v'),None)
if net is None:finish('BLOCKED_MISSING_NATIVE_NETLIST','Official synth no actualnetlist',6)
import hashlib
result['mapped_netlist_sha256']=hashlib.sha256(net.read_bytes()).hexdigest();result['mapped_macro_types']={n:len(re.findall(r'^\s*'+re.escape(n)+r'\s+',net.read_text(),re.M))for n in allowed};result['under_400k_std_cells']=result['mapped_std_cells']<=400000
finish('MAPPED_COUNT_PASS')
