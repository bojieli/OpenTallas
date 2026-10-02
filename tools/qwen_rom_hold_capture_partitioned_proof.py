#!/usr/bin/env python3
"""Conjoin32 bit partitions of the same literal full-geometry HDL miter.

No hardware is resized. Each case retains all80 mask-control replicas and
proves eight bits/column at the chosen intra32-bit chunk offset. Across32
cases this covers every512 output and2560 capture bit; all data/control
inputs remain arbitrary. Existing whole-vector proof jobs stay untouched.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from qwen_rom_hold_capture_literal_gate import ROOT,YOSYS,miter
from qwen_rom_kv_finite_window_gate import guarded_process
BASE=ROOT/'results/uarch/qwen_rom_hold_capture_literal_gate_20261002/literal_build_r1'


def partition(text,offset):
    if not 0<=offset<32:raise ValueError('Offset outside complete partition')
    outputs=[32*c+offset for c in range(16)]
    for other in ['dq','eq']:
        text=text.replace(f'assert(oq=={other});',''.join(f'assert(oq[{bit}]=={other}[{bit}]);' for bit in outputs))
    def caps(match):
        a,lo,b,ro=match.groups();lo=int(lo);ro=int(ro)
        return ''.join(f'assert({a}[{lo+32*c+offset}]=={b}[{ro+32*c+offset}]);' for c in range(8))
    text=re.sub(r'assert\((og)\[(\d+)\+:256\]==(eg|dg|rom_rd)\[(\d+)\+:256\]\);',caps,text)
    if '+:256' in text or 'assert(oq==' in text:raise ValueError('Unpartitioned wide property remains')
    return text,outputs


def run(workdir,result):
    if workdir.exists() or result.exists():raise ValueError('Refusing overwrite')
    workdir.mkdir(parents=True);rows=[]
    original=(BASE/'formal_original.sv').read_bytes();candidate=(BASE/'formal_candidate.sv').read_bytes()
    (workdir/'original.sv').write_bytes(original);(workdir/'candidate.sv').write_bytes(candidate)
    for offset in range(32):
        text,bits=partition(miter(),offset);hdl=workdir/(f'bit{offset}.sv');hdl.write_text(text)
        ys=workdir/(f'bit{offset}.ys');ys.write_text(f'''read_verilog -formal -sv {workdir/'original.sv'} {workdir/'candidate.sv'} {hdl}
prep -top qwen_hold_capture_formal -flatten
async2sync
dffunmap
opt_clean
sat -seq 2 -tempinduct -set-assumes -prove-asserts -verify
''')
        log=workdir/(f'bit{offset}.log');rc,out=guarded_process([YOSYS,'-s',str(ys)],workdir,log)
        passed=rc==0 and 'Induction step proven: SUCCESS!' in out
        rows.append(dict(offset=offset,status='PASS' if passed else 'FAIL',returncode=rc,output_bits=bits,script_sha256=hashlib.sha256(ys.read_bytes()).hexdigest(),miter_sha256=hashlib.sha256(hdl.read_bytes()).hexdigest(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
        print(offset,rows[-1]['status'],flush=True)
        if not passed:break
    covered={bit for r in rows if r['status']=='PASS' for bit in r['output_bits']}
    good=len(rows)==32 and all(r['status']=='PASS' for r in rows) and covered==set(range(512))
    record=dict(schema='opentallas.qwen-rom-hold-capture-partitioned-HDL-proof.v1',status='PASS_ALL32_LITERAL_HDL_PARTITIONS' if good else 'FAIL',source_commit='b9af1afb4',formal_source_sha256={'original':hashlib.sha256(original).hexdigest(),'candidate':hashlib.sha256(candidate).hexdigest()},tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows,covered_output_bits=sorted(covered),capture_bits_covered=2560 if good else None,all80_mask_control_FFs_retained_in_each_source=True,hardware_geometry_changed=False,whole_vector_jobs_preserved=True,PnR=False,adoption=False)
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(record['status']);return 0 if good else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workdir',type=Path,required=True);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args();raise SystemExit(run(a.workdir.resolve(),a.result))
