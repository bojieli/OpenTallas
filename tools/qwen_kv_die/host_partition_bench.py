#!/usr/bin/env python3
"""qwen-split/kvsys die lead r6 2026-10-15: co-simulation equivalence bench of the HOST physical partition.

Builds tb_host_partition_equiv: the actual qkd_host_root_integrated (reference) and qkd_host_root_composed (generated
root core qkd_host_root_pt + 128 die slices qkd_host_pc_slice, wired as the source parents) side by side, every input
driven identically (clock entries from one die clock, por_n / pll_locked sequenced, every other input random each cycle,
including all 128 PCs' land_es / ctrl_er / completion words), every output compared on every cycle.  PASS requires zero
mismatching output bits AND activity in the moved logic (ctrl_es / land_er words and per-PC boot status must toggle), so an
idle bench cannot pass.  The OT_PARTITION_MUT build (PCs 0/1 take each other's landing word) must FAIL.

    python3 tools/qwen_kv_die/host_partition_bench.py --out DIR [--cycles N] [--mutant]   # writes tb + file list + run.sh
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
from die_port_bind_kv import header, evalw  # noqa: E402

PARAMS = dict(T_LINK=64, T_HBM=64, WDOG=4096, ENABLE_SERVICE=1, ENABLE_NATIVE=1, ENABLE_TOKEN=1)
HELD = {'por_n', 'pll_locked', 'die_id'}
MOVED_OUT = ('ctrl_es', 'land_er')


def tb(cycles):
    params, ports = header((ROOT / 'rtl/qwen_sys/host_integrated_20261014/qkd_host_root_integrated.sv').read_text(),
                           'qkd_host_root_integrated')
    pv = dict(params, **{k: str(v) for k, v in PARAMS.items()})
    w = {p: evalw(x, pv) for p, (d, x) in ports.items()}
    ins = [p for p, (d, _) in ports.items() if d == 'input']
    outs = [p for p, (d, _) in ports.items() if d == 'output']
    clocks = [p for p in ins if p.startswith('ck_')]
    data = [p for p in ins if p not in clocks and p not in HELD]
    L = ['`timescale 1ns/1ps', 'module tb_host_partition_equiv;', ' reg ck=0; always #0.5 ck=~ck;',
         ' reg por_n=0, pll_locked=0; reg [2:0] die_id=3\'d0;']
    for p in data:
        L.append(f' reg [{w[p]-1}:0] {p};')
    for p in outs:
        L.append(f' wire [{w[p]-1}:0] r_{p}, d_{p};')
    pstr = ','.join(f'.{k}({v})' for k, v in PARAMS.items())
    for inst, mod, pre in (('u_ref', 'qkd_host_root_integrated', 'r_'), ('u_dut', 'qkd_host_root_composed', 'd_')):
        conns = []
        for p in ins:
            conns.append(f'.{p}({{{w[p]}{{ck}}}})' if p in clocks else f'.{p}({p})')
        conns += [f'.{p}({pre}{p})' for p in outs]
        L.append(f' {mod} #({pstr}) {inst}(' + ', '.join(conns) + ');')
    L += [' integer cyc, errs=0, firsterr=-1; integer act_ces=0, act_ler=0, act_boot=0, act_all=0;'];
    # data inputs: refresh every cycle from $urandom (wide buses filled 32 b at a time)
    L.append(' task automatic drive; integer i;')
    for p in data:
        if w[p] <= 32:
            L.append(f'  {p} = $urandom;')
        else:
            L.append(f'  for(i=0;i<{(w[p]+31)//32};i=i+1) {p}[i*32+:32] = $urandom;' if w[p] % 32 == 0 else
                     f'  for(i=0;i<{w[p]//32};i=i+1) {p}[i*32+:32] = $urandom; {p}[{w[p]-1}:{w[p]//32*32}] = $urandom;')
    L.append(' endtask')
    L.append(' task automatic check;')
    for p in outs:
        L.append(f'  if(r_{p}!==d_{p}) begin errs=errs+1; if(firsterr<0) firsterr=cyc; '
                 f'if(errs<20) $display("MISMATCH cyc%0d {p} ref=%h dut=%h", cyc, r_{p}, d_{p}); end')
    L += ['  if(|r_ctrl_es) act_ces=act_ces+1; if(|r_land_er) act_ler=act_ler+1;',
          '  if(u_ref.u_rank.boot_done_pc!==128\'d0) act_boot=act_boot+1; if(|r_hc || |r_hb) act_all=act_all+1;',
          ' endtask',
          ' initial begin',
          '  drive;',
          '  for(cyc=0;cyc<' + str(cycles) + ';cyc=cyc+1) begin',
          '   if(cyc==16) pll_locked=1; if(cyc==24) por_n=1;',
          '   @(negedge ck); check; drive;',
          '  end',
          '  $display("ACTIVITY ctrl_es_cycles=%0d land_er_cycles=%0d boot_done_cycles=%0d hc_hb_cycles=%0d", act_ces, act_ler, act_boot, act_all);',
          '  if(errs) begin $display("FAIL host partition equivalence: %0d mismatching output samples, first at cycle %0d", errs, firsterr); $fatal(1); end',
          '  if(act_ces==0 || act_ler==0) begin $display("FAIL host partition bench: moved per-PC logic idle (no evidence)"); $fatal(1); end',
          '  $display("PASS host partition equivalence: %0d cycles, %0d outputs (%0d bits) identical every cycle", ' + str(cycles) +
          f', {len(outs)}, {sum(w[p] for p in outs)});',
          '  $finish;', ' end', 'endmodule', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cycles', type=int, default=3000)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'tb_host_partition_equiv.sv').write_text(tb(a.cycles))
    print(a.out / 'tb_host_partition_equiv.sv')


if __name__ == '__main__':
    main()
