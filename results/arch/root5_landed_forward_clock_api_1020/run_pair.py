from pathlib import Path
import subprocess,concurrent.futures,json,time,os
root=Path.cwd()
def run(label):
 start=time.time()
 with (root/(label+'.pytest.log')).open('w') as f:
  p=subprocess.run(['python3','-m','pytest','tools/ref_tile/tests','-q','--junitxml='+str(root/(label+'.pytest.xml'))],cwd=root/label,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONPATH=str(root/"testdeps")))
 return dict(label=label,rc=p.returncode,seconds=time.time()-start)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results=list(pool.map(run,['baseline','candidate']))
(root/'PAIR_RESULTS.json').write_text(json.dumps(results,indent=2));print(json.dumps(results),flush=True)
