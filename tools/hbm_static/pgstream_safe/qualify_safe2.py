#!/usr/bin/env python3
"""Fleet actual parent positives and causal mutants; immutable separate outputs."""
from pathlib import Path
import json
import subprocess
import sys

out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
cases=[('rr18',0,1,18,15,2),('rr10',0,1,10,7,2),('qid0',0,0,18,15,2)]
cases += [('m'+str(mut),mut,1,18,15,2) for mut in (1,2,3,6,8,12,13,14)]
# kitland: the CURRENT regional top behind the CURRENT kit's 3 landing stages (diagnostic, not a pass/fail of SAFE2)
cases += [('kitland_rr18',0,1,18,15,'kitland')]
results=[]
for name,mut,qid,rr,wr,safe in cases:
    cmd=['bash','tools/hbm_static/pgstream_safe/run_safe2.sh',str(out/name),str(mut),str(qid),str(rr),str(wr),'kitland' if safe=='kitland' else 'safe2']
    with (out/(name+'.out')).open('w') as log:
        cp=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    bench=out/name/'bench.log'
    text=bench.read_text() if bench.exists() else ''
    ok=(cp.returncode==0 and 'PG_STREAM_SPLIT PASS checks=' in text) if mut==0 else (cp.returncode!=0 and 'PG_STREAM_SPLIT FAIL errors=' in text)
    results.append(dict(name=name,mut=mut,qid=qid,rr=rr,wr=wr,safe_copy=safe,exit=cp.returncode,expected='fail' if mut else 'pass',matched=ok))
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results[-1]),flush=True)
sys.exit(not all(row['matched'] for row in results if row['safe_copy']!='kitland'))
