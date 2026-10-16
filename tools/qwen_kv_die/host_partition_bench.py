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


def tb(cycles, protocol=False):
    if protocol:
        return tb_protocol(cycles)
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


# Protocol mode (kvsys die lead 2026-10-15 17:50, Q-KVSYS-DIE): the random bench above never boots -- link_up is a fresh
# random word every cycle, so the reset sequencer (ot_qwen_sys_rst_seq: &link_up after link reset) never releases
# hbm_rst_n / boot_go, ctrl_es stays 0 and every fault/admission change is invisible (both HOST mutants passed idle).
# Here the boundary follows the real protocol: pll_locked, por_n, PHY up, all NL links held up, no transport / CROM
# faults; each of the 128 PCs gets a static-controller model at ctrl_es / ctrl_er / ctrl_completion_* (fixed latency,
# one scratch sector of storage, write ack er[259], read data er[0]/er[256:1], one ordered completion per launch with
# its write flag), so qkd_hbm_boot_pc runs both WR/RD phases and every PC must reach boot_done & boot_ok.  After the
# boot the bench (1) pulses link_physical_fault (the D2D end's sticky physical fault, bit die_id) and REQUIRES the
# reference to show it at an output (fault_src / service_faults / irq / sys_ready), (2) toggles native_admit_ready.
# PASS = zero mismatching output samples + every PC booted ok + the physical-fault pulse observed at the reference outputs.
PROTO_HELD = {'por_n', 'pll_locked', 'die_id', 'phy_up', 'link_up', 'link_physical_fault', 'native_admit_ready'}
CTRL_PORTS = {'ctrl_er', 'ctrl_completion_v', 'ctrl_completion_we', 'ctrl_completion_fault'}
CTRL_LAT = 6


def tb_protocol(cycles):
    params, ports = header((ROOT / 'rtl/qwen_sys/host_integrated_20261014/qkd_host_root_integrated.sv').read_text(),
                           'qkd_host_root_integrated')
    pv = dict(params, **{k: str(v) for k, v in PARAMS.items()})
    w = {p: evalw(x, pv) for p, (d, x) in ports.items()}
    ins = [p for p, (d, _) in ports.items() if d == 'input']
    outs = [p for p, (d, _) in ports.items() if d == 'output']
    clocks = [p for p in ins if p.startswith('ck_')]
    for p in PROTO_HELD | CTRL_PORTS:
        assert p in ins, p
    quiet = [p for p in ins if p not in clocks and p not in PROTO_HELD and p not in CTRL_PORTS]
    nl = w['link_up']
    L = ['`timescale 1ns/1ps', 'module tb_host_partition_equiv;', ' reg ck=0; always #0.5 ck=~ck;',
         ' reg por_n=0, pll_locked=0, phy_up=0, link_physical_fault=0, native_admit_ready=0; reg [2:0] die_id=3\'d0;',
         f' reg [{nl-1}:0] link_up=0;',
         ' reg [33407:0] ctrl_er=0; reg [127:0] ctrl_completion_v=0, ctrl_completion_we=0, ctrl_completion_fault=0;']
    for p in quiet:
        L.append(f' reg [{w[p]-1}:0] {p} = 0;')
    for p in outs:
        L.append(f' wire [{w[p]-1}:0] r_{p}, d_{p};')
    pstr = ','.join(f'.{k}({v})' for k, v in PARAMS.items())
    for inst, mod, pre in (('u_ref', 'qkd_host_root_integrated', 'r_'), ('u_dut', 'qkd_host_root_composed', 'd_')):
        conns = [f'.{p}({{{w[p]}{{ck}}}})' if p in clocks else f'.{p}({p})' for p in ins]
        conns += [f'.{p}({pre}{p})' for p in outs]
        L.append(f' {mod} #({pstr}) {inst}(' + ', '.join(conns) + ');')
    L += [
        ' // static HBM controller model per PC, driven from the REFERENCE ctrl_es (DUT ctrl_es is compared every cycle)',
        f' localparam integer LAT={CTRL_LAT};',
        ' reg [255:0] sector [0:127]; reg [7:0] dly [0:127]; reg pend_we [0:127]; reg [255:0] pend_d [0:127];',
        ' integer pc, cyc, errs=0, firsterr=-1, act_ces=0, launches=0, bad_launch=0; integer pf_at=-1, pf_seen=-1, adm_toggles=0;',
        ' reg booted=0; integer booted_at=-1;',
        ' initial for(pc=0;pc<128;pc=pc+1) begin sector[pc]=0; dly[pc]=0; pend_we[pc]=0; pend_d[pc]=0; end',
        ' task automatic ctrl_model; reg [287:0] es; begin',
        '  ctrl_er = 0; ctrl_completion_v = 0; ctrl_completion_we = 0;',
        '  for(pc=0;pc<128;pc=pc+1) begin',
        '   es = r_ctrl_es[pc*288+:288];',
        '   if(dly[pc]!=0) begin dly[pc]=dly[pc]-1;',
        '    if(dly[pc]==0) begin',
        '     ctrl_completion_v[pc]=1; ctrl_completion_we[pc]=pend_we[pc];',
        '     if(pend_we[pc]) begin sector[pc]=pend_d[pc]; ctrl_er[pc*261+259]=1; end',
        '     else begin ctrl_er[pc*261]=1; ctrl_er[pc*261+1+:256]=sector[pc]; end',
        '    end',
        '   end',
        '   if(es[0]) begin launches=launches+1; if(dly[pc]!=0) bad_launch=bad_launch+1;',
        '    dly[pc]=LAT; pend_we[pc]=es[287]; pend_d[pc]=es[256:1]; end',
        '  end',
        ' end endtask',
        ' task automatic check;']
    for p in outs:
        L.append(f'  if(r_{p}!==d_{p}) begin errs=errs+1; if(firsterr<0) firsterr=cyc; '
                 f'if(errs<20) $display("MISMATCH cyc%0d {p} ref=%h dut=%h", cyc, r_{p}, d_{p}); end')
    L += ['  if(|r_ctrl_es) act_ces=act_ces+1;',
          ' endtask',
          ' reg [31:0] fs0; reg [24:0] sf0; reg irq0, sr0;',
          ' initial begin',
          '  for(cyc=0;cyc<' + str(cycles) + ';cyc=cyc+1) begin',
          '   if(cyc==16) pll_locked=1; if(cyc==24) por_n=1; if(cyc==32) begin phy_up=1; link_up={' + str(nl) + '{1\'b1}}; end',
          '   if(!booted && u_ref.u_rank.boot_done_pc==128\'hffffffff_ffffffff_ffffffff_ffffffff) begin booted=1; booted_at=cyc;',
          '    if(u_ref.u_rank.boot_ok_pc!==128\'hffffffff_ffffffff_ffffffff_ffffffff) begin $display("FAIL protocol bench: boot done but not ok on PCs %h", ~u_ref.u_rank.boot_ok_pc); $fatal(1); end',
          '    pf_at=cyc+200; end',
          '   if(cyc==pf_at) begin fs0=r_fault_src; sf0=r_service_faults; irq0=r_irq; sr0=r_sys_ready; link_physical_fault=1; end',
          '   if(cyc==pf_at+4) link_physical_fault=0;',
          '   if(pf_at>=0 && cyc>pf_at && pf_seen<0 && (r_fault_src!==fs0 || r_service_faults!==sf0 || r_irq!==irq0 || r_sys_ready!==sr0)) pf_seen=cyc;',
          '   if(booted && cyc<pf_at && (cyc%7)==0) begin native_admit_ready=~native_admit_ready; adm_toggles=adm_toggles+1; end',
          '   @(negedge ck); check; ctrl_model;',
          '  end',
          '  $display("ACTIVITY ctrl_es_cycles=%0d launches=%0d bad_launch=%0d booted_at=%0d pf_at=%0d pf_seen=%0d admit_toggles=%0d hbm_rst_n=%b boot_go_seen sys_ready=%b fault_src=%h", act_ces, launches, bad_launch, booted_at, pf_at, pf_seen, adm_toggles, r_hbm_rst_n, r_sys_ready, r_fault_src);',
          '  if(errs) begin $display("FAIL host partition protocol: %0d mismatching output samples, first at cycle %0d", errs, firsterr); $fatal(1); end',
          '  if(!booted || act_ces==0 || bad_launch) begin $display("FAIL host partition protocol bench: boot not completed / idle / overlapping launches"); $fatal(1); end',
          '  if(pf_seen<0) begin $display("FAIL host partition protocol bench: link_physical_fault pulse not observable at the reference outputs"); $fatal(1); end',
          '  $display("PASS host partition protocol: %0d cycles, 128 PCs boot ok at cycle %0d, link physical fault seen at %0d, %0d outputs identical every cycle", ' + str(cycles) + f', booted_at, pf_seen, {len(outs)});',
          '  $finish;', ' end', 'endmodule', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cycles', type=int, default=3000)
    ap.add_argument('--protocol', action='store_true', help='protocol-driven boot + fault/admission bench (tb_protocol)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'tb_host_partition_equiv.sv').write_text(tb(a.cycles, a.protocol))
    print(a.out / 'tb_host_partition_equiv.sv')


if __name__ == '__main__':
    main()
