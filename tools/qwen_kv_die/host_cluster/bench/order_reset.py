#!/usr/bin/env python3
"""Smallest reset-contract vehicle: both full-shape order members versus independent three-edge reset model.

Every output compared across 100 reset epochs, including immediate assertion and each release edge.
The mutant bypasses both DUT relays and must fail the independent release-latency check.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('gen', ROOT / 'tools/qwen_kv_die/host_cluster/gen_prompt_rr.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
MEMBERS = [('qkd_host_ingest_chain_pt', 'rtl/qwen_sys/split_20261014/qkd_host_root_pt.sv'),
           ('qkd_host_boot_dispatch_debt', 'rtl/qwen_sys/host_20261013/qkd_host_boot_dispatch_debt.sv')]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['exact', 'mutant'])
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    text = ['`timescale 1ns/1ps', 'module tb_order_reset;',
            'reg ck=0,rst_n=0; always #0.5 ck=~ck;',
            "reg[2:0]ref_pipe=0; always @(posedge ck or negedge rst_n) if(!rst_n)ref_pipe<=0; else ref_pipe<={ref_pipe[1:0],1'b1};",
            'integer errors=0,comparisons=0,epochs=0,emits=0;']
    checks, drive = [], []
    for i, (mod, src) in enumerate(MEMBERS):
        _, header = gen.header(src, mod)
        ports = gen.ports(header)
        dcon, rcon = [], []
        for direction, rng, name in ports:
            if name.startswith('ck'):
                dn = rn = 'ck'
            elif name == 'rst_n':
                dn, rn = 'rst_n', 'ref_pipe[2]'
            elif direction == 'input':
                dn = rn = f'i{i}_{name}'
                text += [f'reg {rng} {dn}=0;']
                drive += [f'{dn} = {{16{{$random}}}};']
                if name in ('chain_a', 'slice_ack', 'acks', 'chain_c', 'chain_fault_i', 'kv_cr', 'hb_cr', 'marker_cr', 'boot_release'):
                    drive += [f'{dn}=0;']
                if name == 'ing':
                    drive += [f'{dn}[33:2] = $urandom_range(0,127); {dn}[1]=1; {dn}[0]=(c%8==0);']
            else:
                dn, rn = f'd{i}_{name}', f'r{i}_{name}'
                text += [f'wire {rng} {dn}, {rn};']
                checks += [f'if({dn} !== {rn}) errors++;']
                if name in ('chain_f', 'kv'):
                    checks += [f'if({dn}[0]) emits++;']
            dcon += [f'.{name}({dn})']
            rcon += [f'.{name}({rn})']
        text += [f'{mod}_rr dut{i}('+','.join(dcon)+');', f'{mod} ref{i}('+','.join(rcon)+');']
        checks += [f'if(dut{i}.rst_q !== ref_pipe[2]) errors++;']
    text += ['initial begin', 'repeat(3) @(negedge ck);',
             'for(integer c=0;c<10000;c++) begin', '@(negedge ck);',
             'comparisons++;'] + checks + [
             'if(c%100==0) begin #0.1; rst_n=0; epochs++; #0.1;',
             "if(dut0.rst_q!==1'b0 || dut1.rst_q!==1'b0)errors++; end",
             'if(c%100==4) rst_n=1;'] + drive + [
             'end',
             '$display("ORDER_RESET %s comparisons=%0d epochs=%0d emits=%0d errors=%0d", (errors==0 && emits>100)?"PASS":"FAIL",comparisons,epochs,emits,errors);',
             'if(errors || emits<=100) $fatal(1,"reset contract mismatch or no traffic"); $finish; end', 'endmodule']
    tb = out / 'tb.sv'
    tb.write_text('\n'.join(text)+'\n')
    sources = json.loads((ROOT / 'physical/ref_tile/qkd_hr_core_order/spec.json').read_text())['sources']
    v = str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator')
    cmd = [v,'--binary','--timing','-j','4','--top-module','tb_order_reset','-Wno-fatal','-Wno-lint','-Wno-style',
           '-Mdir',str(out/'obj'),'-o','tb']
    if a.mode == 'mutant': cmd += ['-DQKD_HR_ORD_RR_MUTANT']
    with (out/'build.log').open('w') as f:
        r = subprocess.run(cmd+[str(tb)]+[str(ROOT/s) for s in sources], stdout=f, stderr=subprocess.STDOUT)
    if r.returncode: sys.exit('ORDER_RESET BUILD_ERROR '+(out/'build.log').read_text()[-2500:])
    r = subprocess.run([str(out/'obj/tb')],capture_output=True,text=True)
    print(r.stdout+r.stderr,flush=True)
    sys.exit(r.returncode != 0)

if __name__ == '__main__': main()
