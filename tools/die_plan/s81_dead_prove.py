#!/usr/bin/env python3
"""Prove current S81 masked leaf inputs unread, using exact source bodies and parameters.

Only the selected parent body is elaborated. Children have their real declared
interfaces and are conservative blackboxes: every input is treated as a load.
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from dead_inputs import dead_bits,module_hash

def ranges(bits):
 out=[]
 for i in sorted(bits):
  if out and i==out[-1][1]+1:out[-1][1]=i
  else:out.append([i,i])
 return out

def extract(text,mod):
 return re.search(r'^module\s+'+re.escape(mod)+r'\b.*?^endmodule',text,re.M|re.S).group()

def run(root,instances,stubs,out):
 root=pathlib.Path(root);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False)
 man=json.loads((root/'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_text())
 src={}
 wanted={'dsdv_svc_sx','dsdv_svc_rs_up','dsdv_pv_so_ingress','dsdv_pv_so_program'}
 for f in man['prefer']:
  p=root/f
  if not p.is_file():continue
  text=p.read_text()
  for n in wanted:
   if re.search(r'^module\s+'+n+r'\b',text,re.M):src[n]=(f,extract(text,n))
 # Dependency bodies are never assumed. Each actual current repository
 # declaration becomes an opaque child; every input remains a live load.
 deps = ['dsdv_svc_sx_hrow','dsdv_sx_rly_in','dsdv_sx_rly_out','ot_sram_1r1w_32x64_m1']
 dep_sources = {}
 for f in man['prefer']:
  p = root/f
  if not p.is_file(): continue
  text = p.read_text()
  for n in deps:
   if re.search(r'^module\s+'+n+r'\b',text,re.M): dep_sources[n]=(f,extract(text,n))
 fallback='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v'
 if 'ot_sram_1r1w_32x64_m1' not in dep_sources:
  dep_sources['ot_sram_1r1w_32x64_m1']=(fallback,extract((root/fallback).read_text(),'ot_sram_1r1w_32x64_m1'))
 if set(dep_sources)!=set(deps): raise ValueError('missing current dependency headers: '+str(set(deps)-set(dep_sources)))
 stubtext='\n'.join(body[:body.index(');')+2]+'\nendmodule\n' for _,body in dep_sources.values())
 defines = man['defines']
 if 'SVCQ_ENG_FG3' in defines: raise ValueError('legacy simulation engine define is not a closing source proof')
 declarations=[];cache={}
 for row in json.loads(pathlib.Path(instances).read_text()):
  mt=re.match(r'(\w+) #\((.*)\) \w+ \(',row['line']);mod=mt[1]
  if mod not in wanted:continue
  params=dict(re.findall(r'\.(\w+)\(([^)]+)\)',mt[2]));key=(mod,tuple(sorted(params.items())))
  if key not in cache:
   d=out/('p'+str(len(cache)));d.mkdir()
   text=re.sub(r'^module\s+'+mod+r'\b.*?^endmodule','',stubtext,flags=re.M|re.S)+'\n'+src[mod][1]+'\n'
   (d/'input.sv').write_text(text)
   overrides=' '.join('-G '+k+'='+v for k,v in params.items())+' '+' '.join('-D '+v for v in defines)
   script=f'read_slang --keep-hierarchy --empty-blackboxes --allow-use-before-declare --top {mod} {overrides} {d}/input.sv\nproc\nopt\nwrite_json {d}/opt.json\n'
   (d/'run.ys').write_text(script)
   with (d/'yosys.log').open('w') as log:
    subprocess.run(['yosys','-Q','-T','-s',str(d/'run.ys')],stdout=log,stderr=log,check=True)
   m=json.loads((d/'opt.json').read_text())['modules'][mod]
   ports={pn:ranges(dead_bits(m,pn)) for pn,p in m['ports'].items() if p['direction']=='input' and dead_bits(m,pn)}
   cache[key]=ports
   print(mod,params,'dead',sum(hi-lo+1 for v in ports.values() for lo,hi in v),flush=True)
  declarations.append(dict(partition_type=row['type'].removeprefix('s81p_'),module=mod,parameters=params,source=src[mod][0],module_sha256=module_hash(root/src[mod][0],mod),method='yosys.proc.opt.no_fanout',remaining_loads=0,ports=cache[key]))
 rec=dict(schema='opentallas.dead_inputs.v1',verdict='PASS',defines=defines,dependency_modules=[dict(module=n,source=f,module_sha256=module_hash(root/f,n),assumption='opaque child: all inputs conservatively live') for n,(f,_) in dep_sources.items()],source_commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),note='Exact optimized top-module ports. Every opaque child input is conservatively live; output aliases are live. Per-type declarations only; no functional ports removed or extra type created.',declarations=declarations)
 (out/'proof.json').write_text(json.dumps(rec,indent=1)+'\n')
 print('S81_DEAD_INPUTS_PROVED',len(declarations),'declarations',len(cache),'specializations',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--instances',required=True);p.add_argument('--stubs',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.root,a.instances,a.stubs,a.out)
