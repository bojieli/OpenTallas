#!/usr/bin/env python3
"""Existing fullNL128 numerical oracle, off and structural cuts, reused builds."""
import argparse, importlib.util, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
P=HERE/'results/rtl/hbm_accel_fmax_inventory_20261004/noc/coll/run_coll_f12.py'
spec=importlib.util.spec_from_file_location('oldgate',P);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False); rows={};ok=True
    for enabled in (0,1):
        d=a.work/f'cuts{enabled}';d.mkdir()
        tb=M.BENCH0.read_text().replace('ot_gpu_coll_endpoint #(.ENABLE(1)',
            f'ot_gpu_coll_endpoint_f12_cuts #(.XREG(1), .TX_MASK_LA(1), .RXOH({enabled}), .RDUP({16 if enabled else 8}), .ENABLE(1)')
        bench=d/'tb_gpu_coll.sv';bench.write_text(tb);M.RC.BENCH=bench
        M.RC.RTL=M.RC.OURS+M.RC.REUSED+M.NEW+[HERE/'rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv']
        exe=M.RC.build(d,4,2);rows[str(enabled)]=[]
        for seed in (1,2,3):
            cases=M.RC.make_cases(160,seed);stim=d/f'stim{seed}.hex';out=d/f'out{seed}.txt'
            M.RC.write_stim(cases,stim)
            r=subprocess.run([str(exe),f'+stim={stim}',f'+out={out}',f'+verilator+seed+{seed}'],cwd=d,capture_output=True,text=True)
            (d/f'sim{seed}.log').write_text(r.stdout+r.stderr)
            ck=M.RC.check(cases,out.read_text() if out.exists() else '')
            good=r.returncode==0 and ck['n_fail']==0 and ck['done'] is not None and ck['done'][0]==0
            rows[str(enabled)].append(dict(seed=seed,n_fail=ck['n_fail'],n_cases=len(ck['cases']),done=ck['done'],
                passed=good,latency_sm=[c['latency_sm'] for c in ck['cases'] if c['measure']]))
            ok &= good
    ok &= all(a['latency_sm']==b['latency_sm'] for a,b in zip(rows['0'],rows['1']))
    files=[*M.RC.OURS,*M.RC.REUSED,*M.NEW,HERE/'rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv',M.BENCH0,P,
           HERE/'tools/gpu_sys/run_coll.py',Path(__file__),HERE/'tools/uarch_model.py']
    result=dict(verdict='PASS_FULLSHAPE_ENDPOINT_EXACT' if ok else 'FAIL',rows=rows,
        added_cycles_per_record=0,added_cycles_per_collective=0,fullshape_NL=128,
        same_existing_golden=True,contextual_SS_FF=False,adoption=False,
        source_sha256={str(f.relative_to(HERE)):M.RC.sha(f) for f in files})
    (a.work/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
