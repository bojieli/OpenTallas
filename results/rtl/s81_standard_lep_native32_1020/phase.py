import concurrent.futures,subprocess,json,os
from pathlib import Path
r=Path.cwd();src=r/'src'
def run(case):
 host,mut=case;out=r/'phase'/f'h{host}_{mut}';out.mkdir(parents=True,exist_ok=True)
 with (out/'driver.log').open('w') as log:p=subprocess.run(['bash','tools/s81_slice/lep_std_phase_bench.sh',str(out),str(host),mut],cwd=src,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,J='2'))
 result=dict(host=host,mut=mut,rc=p.returncode);(out/'result.json').write_text(json.dumps(result)+'\n');print(result,flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(run,[(1,'none'),(0,'none'),(1,'stdsel'),(1,'vskew')]))
(r/'phase_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
