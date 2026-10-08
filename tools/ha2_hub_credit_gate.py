#!/usr/bin/env python3
"""Minimum full-width hub-flight credit gate plus unchanged TU parent guards."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'rtl/hbm_accel/ha2_ar/'
SENDER = [BASE + n + '.sv' for n in (
    'ot_ha2_prims', 'ot_ha2_parent_quiet_prims',
    'ot_ha2_hub_credit_sender', 'tb_ha2_hub_credit_sender')]
PARENT = ['rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
    'rtl/hdc/ot_hdc_fp32_add_lat.sv', BASE+'ot_ha2_prims.sv',
    BASE+'ot_ha2_owner_reduce.sv', BASE+'ot_ha2_owner_reduce_runtime.sv',
    BASE+'ot_ha2_tu_owner_adapter.sv', BASE+'ot_ha2_parent_quiet_prims.sv',
    'rtl/link/ot_link_afifo.sv',
    'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv',
    'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner.sv']
HALF = [BASE+'ot_ha2_tu_owner_banked.sv', BASE+'ot_ha2_tu_owner_banked_half.sv',
    BASE+'ot_ha2_hub_credit_sender.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources=sorted(set(SENDER+PARENT+HALF+[BASE+'tb_ha2_tu_owner_parent.sv','tools/ha2_hub_credit_gate.py']))
    pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources}
    checks = {}
    for name, mutant, stall in [('credit_stalls',0,1), ('no_stalls',0,0),
            ('ignore_reservations',1,1), ('ignore_receiver_credit',2,1)]:
        top = 'tb_ha2_hub_credit_sender'
        cmd = ['iverilog','-g2012','-s',top,f'-P{top}.MUTANT={mutant}',
               f'-P{top}.STALL={stall}','-o',str(out/(name+'.vvp')),*SENDER]
        build = subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        (out/(name+'.compile.log')).write_text(build.stdout+build.stderr)
        if build.returncode:
            raise RuntimeError(f'{name}: compile failed, not a valid negative')
        run = subprocess.run(['vvp',str(out/(name+'.vvp'))],cwd=ROOT,capture_output=True,text=True)
        text = run.stdout+run.stderr
        (out/(name+'.log')).write_text(text)
        correct = (run.returncode==0 and 'PASS_HA2_HUB_CREDIT' in text) if not mutant else (
            run.returncode!=0 and 'CREDIT_FAIL' in text)
        checks[name] = dict(command=cmd,returncode=run.returncode,correct=correct,output=text)
    # These guards use the preserved default hierarchy and original numerical adapter.
    name='default_parent_guards'; top='tb_ha2_tu_owner_parent'
    cmd=['iverilog','-g2012','-s',top,'-o',str(out/(name+'.vvp')),*PARENT,BASE+top+'.sv']
    build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (out/(name+'.compile.log')).write_text(build.stdout+build.stderr)
    if build.returncode: raise RuntimeError('default parent compile failed')
    run=subprocess.run(['vvp',str(out/(name+'.vvp'))],cwd=ROOT,capture_output=True,text=True)
    text=run.stdout+run.stderr
    (out/(name+'.log')).write_text(text)
    checks[name]=dict(command=cmd,returncode=run.returncode,
        correct=run.returncode==0 and 'PASS parent changed-source boundary' in text,output=text)
    # Full16-lane, PF384 endpoint elaboration confirms actual sender and peer ready wiring.
    cmd=['verilator','--lint-only','-Wno-fatal','--top-module','ot_hbm_accel_tu_endpoint_owner',
         '-GENABLE=1','-GOWNER_REDUCER=1','-GOWNER_BANKED_HALF=1','-GPFMAX=384',*PARENT,*HALF]
    build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (out/'half_endpoint.compile.log').write_text(build.stdout+build.stderr)
    checks['half_endpoint_fullshape_elaboration']=dict(command=cmd,returncode=build.returncode,correct=build.returncode==0)
    sources=sorted(set(SENDER+PARENT+HALF+[BASE+'tb_ha2_tu_owner_parent.sv','tools/ha2_hub_credit_gate.py']))
    record=dict(passed=all(c['correct'] for c in checks.values()),checks=checks,
        source_sha256=pins,
        scope='Full-width finite-flight sender exactness and negatives, unchanged default parent guards, fullshape new endpoint elaboration. Not complete endpoint numerical/physical adoption.')
    assert pins=={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources}, 'Source changed during gate'
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(passed=record['passed'],checks={k:v['correct'] for k,v in checks.items()})))
    return 0 if record['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
