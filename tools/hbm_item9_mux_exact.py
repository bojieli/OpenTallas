#!/usr/bin/env python3
"""Full NL128, NSM2/4 original-vs-successor lockstep; no array simulation."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['rtl/gpu_sys/ot_gpu_coll_mux.sv','rtl/gpu_sys/ot_gpu_coll_mux_f12.sv',
       'rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv','rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv',
       'rtl/link/ot_link_afifo.sv',
       'results/rtl/hbm_item9_closure_20261005/tb_coll_mux_owner64_ls.sv']
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
    v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    rows=[]
    for enabled in (0,1):
        d=a.work/f'owner{enabled}';d.mkdir()
        cmd=[str(v),'--binary','--timing','-j','2','-Wno-fatal',
             '--top-module','tb_coll_mux_owner64_ls',f'-GOWNER64={enabled}',
             '-Mdir',str(d/'obj'),*[str(ROOT/f) for f in FILES]]
        r=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'MAKEFLAGS':'-j2'})
        (d/'build.log').write_text(r.stdout+r.stderr)
        if r.returncode: raise SystemExit(f'build FAIL: {d}')
        r=subprocess.run([str(d/'obj/Vtb_coll_mux_owner64_ls'),'+verilator+seed+1'],capture_output=True,text=True)
        (d/'run.log').write_text(r.stdout+r.stderr)
        cfg=re.findall(r'MUXLS owner64=(\d+) nsm=(\d+) cycles=(\d+) grants=(\d+) mismatches=(\d+)',r.stdout)
        passed=r.returncode==0 and len(cfg)==2 and all(int(c[2])==200000 and int(c[3])>0 and int(c[4])==0 for c in cfg)
        rows.append(dict(OWNER64=enabled,pass_exact=passed,configurations=cfg))
    ok=all(r['pass_exact'] for r in rows)
    (a.work/'result.json').write_text(json.dumps(dict(verdict='PASS_FULLSHAPE_MUX_EXACT' if ok else 'FAIL',
        rows=rows,added_mux_cycles=0,scope='all handshakes, payload and responses; NL128 NSM2/4 randomized backpressure',
        endpoint_semantic_gate='reuse unchanged TX_MASK_LA existing exact pin; no new endpoint source',
        source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in [*FILES,'tools/uarch_model.py',str(Path(__file__).relative_to(ROOT))]},
        contextual_SS_FF=False,adoption=False),indent=2)+'\n')
    print((a.work/'result.json').read_text())
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
