import json,sys,os
from pathlib import Path
E=Path('/srv/opentallas-scratch2/claude/codex-qc-xhead-1027');T=E/'tree'
sys.path[:0]=[str(T/'rtl/test/qwen_dv'),str(T/'tools/qwen_layerbench')]
import xhead_bench as X
X.VEC_AGES=X.VB.V.load_ages(E/'cal/vec_ages.json')
log={}
for line in (E/'cal/cal_probe/run_resid_m0.log').read_text().splitlines():
 c,n,h=line.split();log.setdefault(n,[]).append((int(c),int(h.replace('x','0').replace('z','0'),16)))
def captured(work,name,ev,ncyc):
 d=E/'baseline_receipt';d.mkdir(exist_ok=True);p=d/'reconstructed.ev';ev.write(p)
 assert p.read_bytes()==(E/'cal/cal_probe/run_resid_m0.ev').read_bytes(),'producer/compiler event mismatch'
 return log
X._orig_run=captured
rc,st=X.run_family(E/'baseline_receipt','gu',X.plan_free(X.X.bench_hr_arrival(),'gu'),'probe_replay')
v=X.verdict('gu',st,rc);xs=st['hr_plan']['xs'];xt,cw,xl,hf=X.heads_log(log)
taps=sorted({a-b for m in range(12) for a,b in zip(xt[m],xs[m])})
dheads=sorted({cw[m][0][0]-(st['hr_plan']['go']+m) for m in range(12) if cw[m]})
r=dict(scope='One actual bound12-slice producer baseline; not per-consumer/fulltoken qualification',producer_rc=rc,heads_clean=v['ok'],hf=hf,slice_faults=v['slice_faults'],x_tap=taps,d_head=dheads,hr_plan={k:v for k,v in st['hr_plan'].items() if k!='xs'},CW={m:cw[m][:1] for m in range(12)},last_xl={m:max(xl[m]) if xl[m] else None for m in range(12)})
(E/'baseline_receipt/result.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1));raise SystemExit(0 if rc==0 and v['ok'] else 1)
