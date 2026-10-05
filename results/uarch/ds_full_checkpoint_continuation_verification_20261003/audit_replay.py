import sys,os,json,hashlib,subprocess,platform
from pathlib import Path
root=Path.cwd().resolve();sys.path.insert(0,str(root/'tools'));sys.dont_write_bytecode=True
tracked=set(subprocess.check_output(['git','ls-files'],text=True).splitlines())
reads=set()
def hook(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes)):return
 mode=args[1]
 if isinstance(mode,str) and any(c in mode for c in 'wax+'):return
 reads.add(str(Path(os.fsdecode(args[0])).absolute()))
sys.addaudithook(hook)
import ds_full_checkpoint_continuation_plan as P
retained=root/'results/uarch/ds_full_checkpoint_continuation_plan_20261003/r1/model.json'
result=P.reconcile_from_retained(retained)
data=json.dumps(result,sort_keys=True,indent=2).encode()+b'\n'
frozen=(root/'results/uarch/ds_full_checkpoint_continuation_plan_20261003/r6/model.json').read_bytes()
assert data==frozen,'model output differs'
import numpy
repo={};external=[]
for path in sorted(reads):
 p=Path(path)
 if not p.is_file():continue
 try:rel=str(p.relative_to(root))
 except ValueError:external.append(path);continue
 repo[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'git_tracked':rel in tracked,'bytes':p.stat().st_size}
modules={}
for mod in list(sys.modules.values()):
 path=getattr(mod,'__file__',None)
 if not path:continue
 p=Path(path).resolve()
 try:rel=str(p.relative_to(root))
 except ValueError:continue
 if p.suffix=='.py' and p.is_file():modules[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'git_tracked':rel in tracked}
assert all(v['git_tracked'] for v in repo.values()),'untracked dependency'
assert all(v['git_tracked'] for v in modules.values()),'untracked module'
assert all(p.startswith(('/usr/','/lib/','/etc/','/proc/')) for p in external),external
record={'status':'PASS_FRESH_CHECKOUT_BYTEEXACT','commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'model_sha256':hashlib.sha256(data).hexdigest(),'repository_read_files':repo,'repository_loaded_modules':modules,'external_read_files':external,'environment':{'python':sys.version,'numpy':numpy.__version__,'platform':platform.platform()},'external_design_or_payload_reads':[],'actual_provider_constructor':False,'numeric_execution':False}
out=Path('/tmp/ds-continuation-independent-evidence-20261003');(out/'replayed_model.json').write_bytes(data);(out/'read_dependency_closure.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':record['status'],'repo_read_files':len(repo),'loaded_repo_modules':len(modules),'model_sha256':record['model_sha256']}))
