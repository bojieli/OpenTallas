#!/usr/bin/env python3
"""Join terminal native object shards; original archive order and link only."""
import argparse,hashlib,json,shlex,shutil,struct,subprocess,time
from pathlib import Path
import w17_D1_compile_ownership_handoff as ownership
ROOT=Path(__file__).resolve().parents[1]
SOURCE='a93ac5a8c2312266213cc4f119aa2bd99175f52a'
VINC=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
DRIVER=Path('/tmp/opentallas-D1-native-r2-execution-20261002/rtl/test/w17_D1_scope_corrected_probe/native_main_scope.cpp')
DRIVER_SHA='8dcea86e5e2774e1990c26b672ea4125340f58b5ff96a8de825383bc2a6220d1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def receipt_valid(r,node):
 if r.get('verdict')!='PASS_OBJECT_SHARD_ONLY' or r.get('exit_code')!=0 or r.get('missing_targets')!=[]:raise ValueError('Not terminal PASS')
 if r.get('source_head')!=SOURCE or r.get('node')!=node or r.get('runtime_authorized') is not False:raise ValueError('Source/scope')
 if r.get('argv',[])[-1:]!=['D1_'+('LOCAL' if node=='local' else 'VM')+'_SHARD']:raise ValueError('Wrong goal')
 if r.get('input_hashes_verified')!=4353:raise ValueError('Input closure')
def compiler_targets(text):
 result=[]
 for line in text.splitlines():
  if 'g++-11' not in line:continue
  a=shlex.split(line)
  if '-c' not in a:raise ValueError('Unknown compiler command')
  src=a[a.index('-c')+1]
  if not src.endswith('.cpp'):raise ValueError('PCH/header rebuild')
  result.append(Path(a[a.index('-o')+1]).name if '-o' in a else Path(src).with_suffix('.o').name)
 return result
def join_inventory(all_targets,local,remote):
 a,b=ownership.assignments(all_targets)
 if set(local)!=set(a) or set(remote)!=set(b):raise ValueError('Missing/foreign ownership')
 ownership.exclusive(local,remote)
 return [(x,local[x] if x in local else remote[x]) for x in all_targets]
def elf_valid(p):
 with Path(p).open('rb') as f:b=f.read(64)
 if len(b)!=64 or b[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<HH',b,16)!=(1,62):return False
 off=struct.unpack_from('<Q',b,40)[0];width,count=struct.unpack_from('<HH',b,58)
 return off>=64 and width==64 and count>0 and Path(p).stat().st_size>=off+width*count
def run(local,remote,out):
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT):raise ValueError('Dirty join source')
 for node,p in [('local',local),('VM',remote)]:receipt_valid(json.loads((p/'verdict.json').read_text()),node)
 if sha(DRIVER)!=DRIVER_SHA:raise ValueError('Driver pin')
 if out.exists():raise ValueError('Fresh join output required')
 available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 if available<128*2**30 or shutil.disk_usage(out.parent).free<48*2**30:raise ValueError('Capacity')
 # Controller must additionally verify terminal services/cgroups and transport SHA.
 names=ownership.targets((local/'obj/Vtb_D1_scope_core_classes.mk').read_text());a,b=ownership.assignments(names)
 ordered=join_inventory(names,{x:local/'obj'/x for x in a},{x:remote/'obj'/x for x in b});verified=[]
 for name,p in ordered:
  if not elf_valid(p):raise ValueError('Invalid/incomplete ELF: '+name)
  verified.append({'target':name,'sha256':sha(p),'bytes':p.stat().st_size,'owner':'local' if name in a else 'VM'})
 out.mkdir();shutil.copytree(local/'obj',out/'obj',copy_function=shutil.copy2)
 for name,p in ordered:
  if name in b:
   shutil.copy2(p,out/'obj'/name);dep=p.with_suffix('.d')
   if not dep.exists():raise ValueError('Missing dependency')
   shutil.copy2(dep,out/'obj'/dep.name)
 for row in verified:
  if sha(out/'obj'/row['target'])!=row['sha256']:raise ValueError('Merge changed object')
 (out/'ordered_objects.json').write_text(json.dumps(verified,indent=2)+'\n')
 args=['make','-C',str(out/'obj'),'-f','Vtb_D1_scope_core.mk','CXX=/usr/bin/g++-11','OPT_FAST=-O0','OPT_SLOW=-O0','OPT_GLOBAL=-O0','Vtb_D1_scope_core__ALL.a']
 dry=subprocess.run(args[:1]+['-n']+args[1:],capture_output=True,text=True,check=True);(out/'archive_dryrun.log').write_text(dry.stdout+dry.stderr)
 if compiler_targets(dry.stdout) or '-x c++-header' in dry.stdout:raise ValueError('Archive would recompile')
 receipt={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'node_source_head':SOURCE,'objects':len(verified),'archive_compiler_commands':0,'runtime_authorized':False,'steps':[],'wall_limit':None,'per_file_limit':None,'per_process_AS':None}
 def step(name,argv):
  start=time.monotonic()
  with (out/(name+'.log')).open('wb') as log:rc=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT).returncode
  receipt['steps'].append({'phase':name,'argv':argv,'exit_code':rc,'wall_s':time.monotonic()-start});(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
  if rc:raise RuntimeError('Native '+name+' FAIL; preserved without retry')
 step('archive',args);archive=out/'obj/Vtb_D1_scope_core__ALL.a'
 if subprocess.check_output(['ar','t',str(archive)],text=True).splitlines()!=names:raise ValueError('Archive order/coverage')
 link=['/usr/bin/g++-11','-std=c++20','-O2','-fcoroutines','-pthread','-I'+str(out/'obj'),'-I'+str(VINC),'-I'+str(VINC/'vltstd'),str(DRIVER),'-Wl,--start-group',str(archive),'-Wl,--end-group']+[str(VINC/x) for x in ['verilated.cpp','verilated_threads.cpp','verilated_timing.cpp','verilated_dpi.cpp']]+['-o',str(out/'D1_current_prefix')]
 step('link',link);receipt.update(verdict='PASS_NATIVE_PREFIX_LINK_ONLY',archive_sha256=sha(archive),binary_sha256=sha(out/'D1_current_prefix'),numerical_credit=False,full_program=False,runtime_started=False);(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--local',type=Path,required=True);p.add_argument('--remote-copy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.local,a.remote_copy,a.out)
