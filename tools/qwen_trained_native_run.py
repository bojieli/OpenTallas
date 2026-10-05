#!/usr/bin/env python3
"""Opt-in complete trained Qwen native token execution, no golden inputs or RTL claim."""
import argparse,hashlib,json,os,re,resource,subprocess,time
from pathlib import Path
import numpy as np
from qwen_trained_byte_provider import ROOT,ARTIFACT,native,canonical,sha,TrainedByteBackend
import importlib.util

def validate_admission(a,go_commit):
 if a.get('schema')!='opentallas.Qwen.trained-native.admission.v1'or a.get('admitted')is not True:raise ValueError('fresh trained-native resource GO required')
 if a['source_commit']!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()or subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):raise ValueError('clean pinned trained-native source required')
 if a['wall_limit_s']is not None or a['FSIZE']!='unlimited'or a['RLIMIT_AS']!='unlimited':raise ValueError('persistent costly-job policy requires unlimited wall/FSIZE/AS')
 for limit in (resource.RLIMIT_FSIZE,resource.RLIMIT_AS):
  if resource.getrlimit(limit)[0]!=resource.RLIM_INFINITY:raise ValueError('inherited restrictive resource limit')
 if set(os.sched_getaffinity(0))!=set(a['cpus']):raise ValueError('real admitted kernel affinity required')
 for name,pin in a['source_sha256'].items():
  if sha(ROOT/name)!=pin:raise ValueError('admitted source changed')
 mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
 if mem<a['fresh_host_headroom_bytes']:raise ValueError('fleet measured headroom admission no longer holds')
 cg=next(x.split(':',2)[2]for x in Path('/proc/self/cgroup').read_text().splitlines()if x.startswith('0::'));base=Path('/sys/fs/cgroup')/cg.lstrip('/')
 if a['unit']not in cg.split('/')or (base/'memory.max').read_text().strip()!=str(a['memory_bytes'])or (base/'memory.swap.max').read_text().strip()!='0':raise ValueError('admitted cgroup memory/swap mismatch')
 info=subprocess.check_output(['systemctl','--user','show',a['unit'],'--property=RuntimeMaxUSec,LimitFSIZE,LimitAS'],text=True)
 fields=dict(x.split('=',1)for x in info.splitlines())
 if fields.get('RuntimeMaxUSec')!='infinity'or fields.get('LimitFSIZE')!='infinity'or fields.get('LimitAS')!='infinity':raise ValueError('costly service must have unlimited runtime/FSIZE/AS')
 go=subprocess.check_output(['git','show',go_commit+':'+a['admission_record_path']],cwd=ROOT)
 if json.loads(go)!=a:raise ValueError('committed admission mismatch')

def guard(a,directory,remaining_bytes=0,known_output_bytes=None):
 directory=Path(directory);parent=directory if directory.exists()else directory.parent;v=os.statvfs(parent)
 if v.f_bavail*v.f_frsize<a['disk_headroom_bytes']+remaining_bytes:raise ValueError('actual inventory/disk headroom exhausted; preserve progress')
 used=known_output_bytes if known_output_bytes is not None else (sum(p.stat().st_size for p in directory.rglob('*')if p.is_file())if directory.exists()else 0)
 if used>a['aggregate_output_bytes']:raise ValueError('admitted aggregate fleet output exhausted; preserve progress')

def run(images,out,admission,go_commit,bounded_module,token=9707):
 validate_admission(admission,go_commit);n=native()
 modulepath=ROOT/bounded_module
 if Path(bounded_module).name=='h3_qwen_complete_native.py' or sha(modulepath)!=admission['source_sha256'].get(str(bounded_module)):raise ValueError('explicit relocated bounded interface pin required')
 spec=importlib.util.spec_from_file_location('trained_qwen_bounded_interface',modulepath);interface=importlib.util.module_from_spec(spec);spec.loader.exec_module(interface)
 if n['source_program']['config']['num_hidden_layers']!=36 or len(n['operations'])!=1737:raise ValueError('full native program required')
 out=Path(out);out.mkdir(parents=True,exist_ok=False);backend=TrainedByteBackend(images,n);machine=interface.TiledMachine(n,interface.HBMByteTileProvider(backend));start=time.monotonic();outputs=[];names={v['version']:v['name']for v in n['operands']}
 (out/'admission.json').write_bytes(canonical(admission));(out/'image_manifest_identity.json').write_bytes(canonical(dict(path=str(Path(images).resolve()),sha256=sha(Path(images)/'manifest.json'))))
 try:
  def observe(op,store):
   guard(admission,out)
   # Hash produced native words after publication; never supply expected values back.
   entries=[]
   for version in op['writes']:
    shape,kind=store.shapes[version];count=2 if kind=='winner'else int(np.prod(shape));digest=hashlib.sha256();name=names[version]
    capture=bool(re.fullmatch(r'L\d+\.X|head\.norm|head\.d[01]\.scaled',name));parts=[]
    if version in store.control:digest.update(canonical(store.control[version]))
    else:
     for i in range(0,count,128):
      words=store.read(version,i,min(128,count-i));digest.update(words.tobytes())
      if capture:parts.append(words.copy())
    if capture:np.save(out/(name+'.npy'),np.concatenate(parts).reshape(shape),allow_pickle=False)
    entries.append(dict(version=version,shape=shape,sha256=digest.hexdigest()))
   r=dict(pc=op['pc'],opcode=op['opcode'],outputs=entries,elapsed_s=time.monotonic()-start,provider=backend.observations());outputs.append(r)
   with(out/'native_progress.jsonl').open('a')as f:f.write(json.dumps(r,sort_keys=True)+'\n');f.flush()
   print(json.dumps(dict(event='NATIVE_PC_RETIRED',pc=op['pc'],opcode=op['opcode'],elapsed_s=r['elapsed_s'])),flush=True)
  result=machine.run(token,0,observer=observe)
  if result['PCs']!=1737 or backend.active is not None:raise ValueError('incomplete native retirement')
  # Independent comparison begins only after the entire native token retires.
  comparisons=compare_after_execution(n,backend.manifest['identity']['snapshot'],out,token,result['next_token'])
  terminal=dict(schema='opentallas.Qwen.trained-native.terminal.v1',verdict='PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED',native=result,provider=backend.observations(),full_checkpoint_native=True,input_token=token,position=0,layers=36,oracle_callbacks=0,independent_numerical_comparison=True,post_execution_comparisons=comparisons,actual_RTL=False,physical_credit=False,token_rate_credit=False,elapsed_s=time.monotonic()-start)
 except BaseException as e:
  terminal=dict(schema='opentallas.Qwen.trained-native.terminal.v1',verdict='FAIL_INCOMPLETE',error=repr(e),provider=backend.observations(),actual_RTL=False,elapsed_s=time.monotonic()-start)
  (out/'terminal.json').write_bytes(canonical(terminal));raise
 (out/'terminal.json').write_bytes(canonical(terminal));return terminal
def compare_after_execution(n,snapshot,out,token,next_token):
 from qwen_hbm_complete_executor import CheckpointWeights
 from qwen_hbm_complete_reference import PostExecutionReference
 weights=CheckpointWeights(n['source_program'],snapshot);reference=PostExecutionReference(n['source_program'],weights);reference.start_token(token,0)
 try:
  for layer in range(36):reference.layer(layer,np.load(out/f'L{layer}.X.npy',allow_pickle=False))
  reference.final_norm(np.load(out/'head.norm.npy',allow_pickle=False))
  for die in range(2):reference.head(die,np.load(out/f'head.d{die}.scaled.npy',allow_pickle=False))
  if reference.next_token!=next_token:raise ValueError('independent final token mismatch')
  return reference.comparisons
 finally:
  (out/'post_execution_comparisons.json').write_bytes(canonical(reference.comparisons));(out/'reference_source_provenance.json').write_bytes(canonical(weights.provenance()))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--images',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admission',type=Path,required=True);ap.add_argument('--token',type=int,default=9707);ap.add_argument('--go-commit',required=True);ap.add_argument('--bounded-module',type=Path,required=True);a=ap.parse_args();run(a.images,a.out,json.loads(a.admission.read_text()),a.go_commit,a.bounded_module,a.token)
