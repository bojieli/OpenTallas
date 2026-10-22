import json,sys,subprocess,tarfile,os,hashlib
from pathlib import Path
base=Path(__file__).resolve().parent
kind=sys.argv[1];root=base/kind;root.mkdir(exist_ok=True)
with tarfile.open(base/(kind+'.tar')) as t:t.extractall(root,filter='data')
refs=json.loads((base/'fixture_refs.json').read_text())
def git(*args,**kw):return subprocess.run(['git','-C',str(root),*args],check=True,**kw)
git('init','-q')
with (base/'test-objects.pack').open('rb') as inp:git('unpack-objects','-q',stdin=inp)
git('update-ref','refs/heads/test',refs[kind]);git('symbolic-ref','HEAD','refs/heads/test')
git('update-ref','refs/remotes/origin/claude/sfuk9-1018',refs['origin/claude/sfuk9-1018'])
# Original commit/tree/blob objects, not proxy Git refs: historical benches read
# their actual pinned source blobs through Git in this sparse test snapshot.
paths=sorted(str(p.relative_to(root)) for d in ('tools/hbm_die_v15','tools/hbm_die_v16')
             for p in (root/d).rglob('test*.py') if p.name!='test_reach_geometry_coverage.py')
(root/'common_test_list.json').write_text(json.dumps(paths,indent=2)+'\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(base/'pytest_lib')+os.pathsep+str(root/'tools'))
import ast
outdir=base/(kind+'_perfile');outdir.mkdir(exist_ok=True)
results=[]
print('COHORT',kind,'commit',refs[kind],'files',len(paths),flush=True)
for i,path in enumerate(paths):
    tree=ast.parse((root/path).read_text())
    structured=any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test') for n in ast.walk(tree))
    cmd=([sys.executable,'-m','pytest','-q','--junitxml='+str(outdir/(str(i)+'.xml')),path]
         if structured else [sys.executable,path])
    with (outdir/(str(i)+'.log')).open('w') as log:
        p=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    results.append(dict(file=path,mode='pytest' if structured else 'script',returncode=p.returncode,log=str(i)+'.log'))
    print('FILE',path,p.returncode,flush=True)
(base/(kind+'_results.json')).write_text(json.dumps(dict(commit=refs[kind],results=results),indent=2)+'\n')
if kind=='candidate':
    q=subprocess.run([sys.executable,'tools/hbm_die_v16/test_reach_geometry_coverage.py'],cwd=root,env=env)
    print('NEW_GUARD_EXIT',q.returncode,flush=True)
print('COHORT_DONE',kind,'files',len(results),'failed',sum(r['returncode']!=0 for r in results),flush=True)
sys.exit(1 if any(r['returncode']!=0 for r in results) else 0)
