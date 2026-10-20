import concurrent.futures,subprocess,json,os
from pathlib import Path
root=Path.cwd();source=root/'src';source.mkdir(exist_ok=True)
# Existing explicit source snapshot now pinned ef97000e9; preserve a64 archive.
ver=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
print(subprocess.check_output([str(ver),'--version'],text=True),flush=True)
cases=[('lep','none',1),('lep_host','none',3),('lep_nh','none',5),('lep_nhr','none',7),
 ('lep','stdsel',1),('lep','vskew',1),('lep','swap',1),('lep','nopair',1),
 ('lep_host','ksoff',3),('lep_host','hdrop',3),('lep_nh','nhacc',5)]
def run(case):
 b,m,s=case;name=f'{b}_{m}_{s}';out=root/'benches_v4'/name;out.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,STD_NATIVE32='1',J='2')
 with (out/'driver.log').open('w') as log:p=subprocess.run(['bash','tools/s81_slice/lep_bench.sh',str(out),m,str(s),b],cwd=source,stdout=log,stderr=subprocess.STDOUT,env=env)
 result=dict(bench=b,mutant=m,seed=s,rc=p.returncode,passed=p.returncode==0)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(run,cases))
(root/'bench_summary_v4.json').write_text(json.dumps(results,indent=2)+'\n')
