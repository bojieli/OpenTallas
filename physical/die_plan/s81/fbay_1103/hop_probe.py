#!/usr/bin/env python3
"""S81-FBAY-1 pre-build hop probe: one relay hop of the FIXED-BAY station form timed in OpenSTA on the ASAP7 libs.
Hop = launch DFF (bay j) -> [lockup DLL, same bay] -> repeated wire (fixed repeaters, equal spacing) -> capture DFF (bay j+1).
Wire = per-segment 4-section RC ladder from the kit RCX table (setRC_rcx.tcl).  Ideal clocks; skew/duty added in the table.
usage: hop_probe.py OUTDIR   (writes hop_<case>.v/.spef/.tcl; run_all.sh runs sta in docker)"""
import sys, os, math
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
RC = {"M5": (0.0189935, 0.098), "M7": (0.0125096, 0.0925), "M4": (0.0180365, 0.1275), "M6": (0.0118796, 0.1305)}
CASES = []
for L in (307, 405):
    for lay in ("M5", "M7"):
        for buf, sp in (("BUFx4_ASAP7_75t_R", 100), ("BUFx8_ASAP7_75t_R", 150), ("BUFx12f_ASAP7_75t_R", 205)):
            for lk in (0, 1):
                CASES.append((L, lay, buf, sp, lk))
runs = []
for (L, lay, buf, sp, lk) in CASES:
    name = f"L{L}_{lay}_{buf.split('_')[0]}_{sp}_{'lk' if lk else 'ff'}"
    nseg = max(1, math.ceil(L / sp)); seg = L / nseg
    r, c = RC[lay]
    v = [f"module hop(input clk, input d, output q);", "  wire a, l;"]
    v.append("  DFFHQNx1_ASAP7_75t_R u_l (.CLK(clk), .D(d), .QN(a));")
    src = "a"
    if lk:
        v.append("  DLLx1_ASAP7_75t_R u_lk (.CLK(clk), .D(a), .Q(l));"); src = "l"
    nets = []
    for s in range(nseg):
        n = f"w{s}"; v.append(f"  wire {n};")
        if s == 0:
            v.append(f"  BUFx4_ASAP7_75t_R u_b0 (.A({src}), .Y(w0));".replace("BUFx4_ASAP7_75t_R", buf)) if False else None
        nets.append(n)
    # driver of seg0 = src cell itself (latch/flop drives first segment); repeaters between segments
    drv = {0: ("u_lk" if lk else "u_l", "Q" if lk else "QN")}
    conn_src = src
    body = []
    for s in range(nseg):
        if s > 0:
            body.append(f"  {buf} u_r{s} (.A(w{s-1}_e), .Y(w{s}));")
            drv[s] = (f"u_r{s}", "Y")
    # each segment net: w{s} (driver side) .. w{s}_e (load side) via SPEF; in verilog one net per segment
    v = [f"module hop(input clk, input d, output q);"]
    v.append("  wire a, l;")
    for s in range(nseg): v.append(f"  wire s{s};")
    v.append("  DFFHQNx1_ASAP7_75t_R u_l (.CLK(clk), .D(d), .QN(" + ("a" if lk else "s0") + "));")
    if lk: v.append("  DLLx1_ASAP7_75t_R u_lk (.CLK(clk), .D(a), .Q(s0));")
    for s in range(1, nseg): v.append(f"  {buf} u_r{s} (.A(s{s-1}), .Y(s{s}));")
    v.append(f"  DFFHQNx1_ASAP7_75t_R u_c (.CLK(clk), .D(s{nseg-1}), .QN(q));")
    v.append("endmodule")
    open(f"{out}/{name}.v", "w").write("\n".join(v) + "\n")
    # SPEF
    sp_ = ["*SPEF \"IEEE 1481-1998\"", "*DESIGN \"hop\"", "*DATE \"x\"", "*VENDOR \"x\"", "*PROGRAM \"x\"", "*VERSION \"x\"",
           "*DESIGN_FLOW \"x\"", "*DIVIDER /", "*DELIMITER :", "*BUS_DELIMITER [ ]", "*T_UNIT 1 PS", "*C_UNIT 1 FF",
           "*R_UNIT 1 KOHM", "*L_UNIT 1 HENRY", ""]
    for s in range(nseg):
        d_inst, d_pin = (("u_lk", "Q") if lk else ("u_l", "QN")) if s == 0 else (f"u_r{s}", "Y")
        l_inst, l_pin = (f"u_r{s+1}", "A") if s < nseg - 1 else ("u_c", "D")
        R = r * seg; C = c * seg; N = 4
        sp_ += [f"*D_NET s{s} {C:.4f}", "*CONN", f"*I {d_inst}:{d_pin} O", f"*I {l_inst}:{l_pin} I", "*CAP"]
        nodes = [f"{d_inst}:{d_pin}"] + [f"s{s}:{i}" for i in range(1, N)] + [f"{l_inst}:{l_pin}"]
        k = 1
        for i, nd in enumerate(nodes):
            cc = C / N * (0.5 if i in (0, N) else 1.0)
            sp_.append(f"{k} {nd} {cc:.5f}"); k += 1
        sp_.append("*RES")
        for i in range(N):
            sp_.append(f"{i+1} {nodes[i]} {nodes[i+1]} {R/N:.5f}")
        sp_.append("*END"); sp_.append("")
    open(f"{out}/{name}.spef", "w").write("\n".join(sp_) + "\n")
    runs.append((name, nseg, seg))
L = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
for corner in ("TT", "FF"):
    for (name, nseg, seg) in runs:
        t = [f"read_liberty {L}/asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib",
             f"read_liberty {L}/asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz",
             f"read_verilog /w/{name}.v", "link_design hop", f"read_spef /w/{name}.spef",
             "create_clock -name clk -period 833.333 [get_ports clk]", "set_input_transition 40 [get_ports clk]",
             "set_input_delay 0 -clock clk [get_ports d]", "set_output_delay 0 -clock clk [get_ports q]",
             "set_clock_uncertainty 25 -hold [all_clocks]",
             "set ps [get_pins u_c/D]",
             "set s [sta::worst_slack_cmd max]",
             f"puts \"R {corner} {name} nseg {nseg} seg {seg:.1f}\"",
             "report_checks -to u_c/D -path_delay max -format full -fields {slew} -digits 1",
             "report_checks -to u_c/D -path_delay min -format full -fields {slew} -digits 1",
             ]
        if "_lk" in name:
            t += ["report_checks -to u_lk/D -path_delay min -digits 1", "report_checks -to u_lk/D -path_delay max -digits 1"]
        t += ["report_check_types -max_slew -violators", "exit"]
        open(f"{out}/{corner}_{name}.tcl", "w").write("\n".join(t) + "\n")
open(f"{out}/list.txt", "w").write("\n".join(n for n, _, _ in runs) + "\n")
