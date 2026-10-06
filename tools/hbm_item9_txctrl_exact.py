#!/usr/bin/env python3
"""Full128 changed TX control only; reuse measured baseline, never rerun it."""
import argparse,importlib.util,json,subprocess,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
P=HERE/'results/rtl/hbm_accel_fmax_inventory_20261004/noc/coll/run_coll_f12.py'
sp=importlib.util.spec_from_file_location('oldgate',P);M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args()
a.work.mkdir(parents=True,exist_ok=False)
baseline=HERE/'results/rtl/hbm_item9_closure_20261005/endpoint_r2/result.json'
old=json.loads(baseline.read_text());assert old['verdict']=='PASS_FULLSHAPE_ENDPOINT_EXACT'
f=HERE/'rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv'
assert hashlib.sha256(f.read_bytes()).hexdigest()==old['source_sha256'][str(f.relative_to(HERE))]
bench=a.work/'tb_gpu_coll.sv';bench.write_text(M.BENCH0.read_text().replace('ot_gpu_coll_endpoint #(.ENABLE(1)',
 'ot_gpu_coll_endpoint_item9_txctrl #(.TXCTRL(1),.XREG(1),.TX_MASK_LA(1),.RXOH(1),.RDUP(16),.ENABLE(1)'))
M.RC.BENCH=bench
M.RC.RTL=M.RC.OURS+M.RC.REUSED+M.NEW+[HERE/'rtl/gpu_sys/ot_gpu_coll_endpoint_item9_txctrl.sv']
exe=M.RC.build(a.work,4,2);rows=[];ok=True
for seed in (1,2,3):
 cases=M.RC.make_cases(160,seed);stim=a.work/f'stim{seed}.hex';out=a.work/f'out{seed}.txt'
 M.RC.write_stim(cases,stim)
 r=subprocess.run([str(exe),f'+stim={stim}',f'+out={out}',f'+verilator+seed+{seed}'],cwd=a.work,capture_output=True,text=True)
 (a.work/f'sim{seed}.log').write_text(r.stdout+r.stderr)
 ck=M.RC.check(cases,out.read_text() if out.exists() else '')
 lat=[c['latency_sm'] for c in ck['cases'] if c['measure']]
 ref=next(x for x in old['rows']['1'] if x['seed']==seed)
 passed=r.returncode==0 and ck['n_fail']==0 and ck['done'] is not None and ck['done'][0]==0 and lat==ref['latency_sm']
 rows.append(dict(seed=seed,n_cases=len(ck['cases']),n_fail=ck['n_fail'],done=ck['done'],latency_sm=lat,matched_reused_baseline=passed));ok &= passed
files=[*M.RC.RTL,M.BENCH0,P,HERE/'tools/gpu_sys/run_coll.py',Path(__file__)]
(a.work/'result.json').write_text(json.dumps(dict(verdict='PASS_CHANGED_TXCTRL_FULL128' if ok else 'FAIL',rows=rows,new_cycles_per_record=0,new_cycles_per_collective=0,baseline_reused_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),baseline_rerun=False,source_sha256={str(f.relative_to(HERE)):M.RC.sha(f) for f in files},contextual_SS_FF=False,adopted=False),indent=2)+'\n')
raise SystemExit(0 if ok else 1)
