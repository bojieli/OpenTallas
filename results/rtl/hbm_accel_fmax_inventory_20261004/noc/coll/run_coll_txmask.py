#!/usr/bin/env python3
"""One existing seed/checker for default-off and qualified-mask candidate; no new stimulus or oracle."""
import argparse, importlib.util, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('oldgate',HERE/'run_coll_f12.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
ROOT=M.ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
    rows={};ok=True
    cases=M.RC.make_cases(160,1)
    for enabled in (0,1):
        d=a.work/('mask'+str(enabled));d.mkdir()
        tb=M.BENCH0.read_text().replace('ot_gpu_coll_endpoint #(.ENABLE(1)',
            f'ot_gpu_coll_endpoint_f12_txmask #(.XREG(1), .TX_MASK_LA({enabled}), .ENABLE(1)')
        bench=d/'tb_gpu_coll.sv';bench.write_text(tb)
        M.RC.BENCH=bench;M.RC.RTL=M.RC.OURS+M.RC.REUSED+M.NEW+[ROOT/'rtl/gpu_sys/ot_gpu_coll_endpoint_f12_txmask.sv']
        M.RC.write_stim(cases,d/'stim.hex');exe=M.RC.build(d,4,2)
        import subprocess
        r=subprocess.run([str(exe),f'+stim={d/"stim.hex"}',f'+out={d/"out.txt"}','+verilator+seed+1'],cwd=d,capture_output=True,text=True)
        (d/'sim.log').write_text(r.stdout+r.stderr)
        checked=M.RC.check(cases,(d/'out.txt').read_text() if (d/'out.txt').exists() else '')
        rows[str(enabled)]={'n_fail':checked['n_fail'],'n_cases':len(checked['cases']),'done':checked['done'],
            'latency_sm':[c['latency_sm'] for c in checked['cases'] if c['measure']]}
        ok &= r.returncode==0 and checked['n_fail']==0 and checked['done'] is not None and checked['done'][0]==0
    ok &= rows['0']['latency_sm']==rows['1']['latency_sm']
    sources=[*M.RC.OURS,*M.RC.REUSED,*M.NEW,ROOT/'rtl/gpu_sys/ot_gpu_coll_endpoint_f12_txmask.sv',M.BENCH0,
             ROOT/'tools/gpu_sys/run_coll.py',Path(__file__),ROOT/'tools/uarch_model.py']
    a.out.write_text(json.dumps(dict(verdict='PASS' if ok else 'FAIL',scope='One existing 164-case seed, XREG1 default/candidate numerical checker and identical latency',
        rows=rows,sources={str(f.relative_to(ROOT)):M.RC.sha(f) for f in sources}),indent=2)+'\n')
    print(json.dumps(rows),flush=True)
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
