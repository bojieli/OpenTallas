#!/usr/bin/env python3
"""Test actual tile/half output merges with injected hardened-quad result ports.

This gate proves consumer valid/fault qualification, not arithmetic or gate wake
latency. Quad arithmetic is replaced by a boundary model; production bank and
merge RTL are exercised. CG=0 is the true negative for the guarded CG=1 successor.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/test/tb_hbm_att_result_valid.sv',
         'rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv',
         'rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv',
         'rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv']
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--negative-only", action="store_true"); args=ap.parse_args()
    out=ROOT/'results/rtl/hbm_att_result_valid_20261010'
    out.mkdir(parents=True,exist_ok=True)
    runs=[]
    with tempfile.TemporaryDirectory(prefix='att-valid-') as td:
        for cg in ((0,) if args.negative_only else (1,0)):
            exe=Path(td)/'sim.vvp'
            subprocess.run(['iverilog','-g2012','-s','tb_hbm_att_result_valid',
                            f'-Ptb_hbm_att_result_valid.CG={cg}','-o',str(exe)]+
                           [str(ROOT/p) for p in SOURCES],check=True,capture_output=True)
            res=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
            log=res.stdout+res.stderr
            (out/('pass.log' if cg else 'negative_cg0.log')).write_text(log)
            runs.append(dict(CG=cg,returncode=res.returncode,
                             passed='ATT_VALID PASS' in log and res.returncode==0))
    rec=dict(schema='opentallas.hbm_att_result_valid.v1',
             parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
             consumer_mechanism='real die tile/hi merge and output bank',
             quad_vehicle='injected hardened-result boundary; arithmetic outside gate',
             checks=36,heads_required=16,runs=runs,
             physical_status='successor qualification required; old views untouched')
    (out/('negative_gate.json' if args.negative_only else 'gate.json')).write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec))
    if args.negative_only: return 1 if not runs[0]['passed'] else 0
    return 0 if runs[0]['passed'] and not runs[1]['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
