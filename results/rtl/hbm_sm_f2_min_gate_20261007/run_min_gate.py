#!/usr/bin/env python3
"""Run exactly two SMH mechanism gates in a pinned source archive; no time cap."""
import pathlib,json,subprocess,sys,hashlib
src=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
rows=[]
for name,extra in [('stress_positive',[]),('request_leak_negative',['--mut-reqleak','--expect-fail'])]:
 result=out/(name+'.json')
 if result.exists():raise SystemExit('Refusing to overwrite '+str(result))
 cmd=[sys.executable,str(src/'tools/dshbm_sm_pq_seq.py'),'run','--seq','stress','--smh','--nc','8','--active','1','--req-credit','--req-stalls','--build-jobs','4','--workdir',str(out/name),'--out',str(result),*extra]
 with (out/(name+'.log')).open('x') as f:rc=subprocess.run(cmd,cwd=src,stdout=f,stderr=subprocess.STDOUT).returncode
 d=json.loads(result.read_text()) if result.exists() else {};expected='fail' if extra else 'pass';good=rc==0 and d.get('status')==expected and ((d.get('mismatching_ops',0)>0) if extra else d.get('mismatching_ops')==0)
 row=dict(name=name,rc=rc,passed=good,expected_status=expected,actual_status=d.get('status'),mismatching_ops=d.get('mismatching_ops'),total_cycles=d.get('total_cycles'),command=cmd);rows.append(row);print(json.dumps(row),flush=True)
 (out/'campaign.json').write_text(json.dumps(dict(source_commit='f2bae3479',wrapper_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),cases=rows,complete=len(rows)==2,passed=len(rows)==2 and all(r['passed'] for r in rows)),indent=2)+'\n')
 if not good:raise SystemExit(1)
