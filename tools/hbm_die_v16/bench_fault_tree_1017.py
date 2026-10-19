#!/usr/bin/env python3
"""HBM-FAULT 2026-10-17: bench generator for the d4f fault-aggregation tree (the exact tree of hbm_fault_1017.tree():
22 ot_hbm_fault_leaf + ot_hbm_status_join_fa NA 4). Every tree edge gets a seeded random number (0..MAXD) of registered
relay stations (the die planner's stations). For EVERY one of the 157 source bits:
  pulse test  : a one-cycle pulse; die_fault must rise exactly at the computed fixed latency (never earlier), a_cause =
                the region bit, block_ready low; still set 120 edges later (sticky); after an F20 clear (cfg target 125)
                die_fault / a_cause drop within 4 edges and stay low for 192 edges; block_ready returns.
  level test  : (every 8th bit + all sync / stack bits) the source held high across a clear: the fault re-asserts within
                8 edges; after release (+latency) and a clear it stays low.
usage: bench_fault_tree_1017.py OUT_tb.sv [SEED]
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_fault_1017 as H  # noqa: E402

MAXD = 3


def main(out, seed=1017):
    rnd = random.Random(seed)
    T = H.tree()
    QS = H.QS
    srcs = []          # (leaf, input bit index, kind, label)
    leaf_in = {n: [None] * t['N'] for n, t in T.items()}
    D = {}             # edge key -> stations
    for n, t in T.items():
        b = 0
        for (i, port, lo, hi, kind) in t['inputs']:
            d = rnd.randint(0, MAXD)
            D[(n, i, port)] = d
            for k in range(lo, hi):
                if kind == 'C':
                    leaf_in[n][b] = ('C', i, d)
                else:
                    leaf_in[n][b] = ('S', len(srcs), d)
                    srcs.append((n, b, kind, f'{i}.{port}[{k}]'))
                b += 1
    droot = {q: rnd.randint(0, MAXD) for q in QS}
    parent = {n: t['parent'] for n, t in T.items()}

    def up(n):          # edges from leaf n's fault output to die_fault
        p = parent[n]
        if p == 'host_status':
            return droot[n[3:]] + 3
        return D[(p, n, 'fault')] + 2 + up(p)

    lat = [D[(n, srcs[s][3].split('.')[0], srcs[s][3].split('.')[1].split('[')[0])] + (3 if kind == 'S' else 2) + up(n)
           for s, (n, b, kind, _) in enumerate(srcs)]
    region = [QS.index(srcs[s][0][3:5]) for s in range(len(srcs))]
    NS = len(srcs)
    L = []
    L.append('`timescale 1ns/1ps\n`default_nettype none\n')
    L.append('module dly #(parameter integer D=0)(input wire clk, rst_n, input wire i, output wire o);\n'
             ' generate if (D == 0) begin : z assign o = i; end else begin : r\n'
             '  reg [D-1:0] s; always @(posedge clk or negedge rst_n) if (!rst_n) s <= 0; else s <= {s, i};\n'
             '  assign o = s[D-1]; end endgenerate\nendmodule\n')
    L.append(f'module tb;\n parameter integer LMUT = 0;\n parameter integer FMUT = 0;\n localparam integer NS = {NS};\n'
             f' reg clk = 0, rst_n = 0; always #1 clk = ~clk;\n reg [NS-1:0] src = 0;\n reg cfg_v = 0; reg [7:0] cfg_target = 0;\n'
             ' wire block_ready, program_active, program_fault, irq, die_fault; wire [3:0] a_cause;\n')
    for n, t in T.items():
        L.append(f' wire [{t["N"] - 1}:0] in_{n}; wire f_{n};\n')
    for n, t in T.items():
        for b, x in enumerate(leaf_in[n]):
            sig = f'src[{x[1]}]' if x[0] == 'S' else f'f_{x[1]}'
            L.append(f' dly #({x[2]}) d_{n}_{b} (clk, rst_n, {sig}, in_{n}[{b}]);\n')
        L.append(f" ot_hbm_fault_leaf #(.N({t['N']}), .SYNC_MASK(64'h{t['SYNC_MASK']:x}), "
                 f'.MUT(LMUT)) {n} (.clk(clk), .rst_n(rst_n), .in(in_{n}), .fault(f_{n}));\n')
    L.append(' wire [3:0] af;\n')
    for k, q in enumerate(QS):
        L.append(f' dly #({droot[q]}) r_{q} (clk, rst_n, f_fr_{q}, af[{k}]);\n')
    L.append(f" ot_hbm_status_join_fa #(.NT(1), .NF(1), .NH(1), .TGTS(8'd0), .NA(4), .FCLR({H.FCLR}), .FMUT(FMUT)) js (\n"
             '  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .desc_v(1\'b0), .launch_v(1\'b0), .cfg_target(cfg_target),\n'
             "  .t_ready(1'b1), .t_active(1'b0), .t_fault(1'b0), .h_fault(1'b0), .a_fault(af),\n"
             '  .block_ready(block_ready), .program_active(program_active), .program_fault(program_fault), .irq(irq),\n'
             '  .die_fault(die_fault), .a_cause(a_cause));\n')
    L.append(f' integer lat [0:NS-1]; integer reg_of [0:NS-1]; integer lvl [0:NS-1];\n initial begin\n')
    for s in range(NS):
        lv = 1 if (s % 8 == 0 or srcs[s][2] == 'S' or srcs[s][0].startswith('fs_')) else 0
        L.append(f'  lat[{s}] = {lat[s]}; reg_of[{s}] = {region[s]}; lvl[{s}] = {lv};\n')
    L.append(' end\n')
    L.append(r''' integer s, e, errs = 0, nlev = 0;
 task fail(input [8*48-1:0] what, input integer s, input integer e);
  begin errs = errs + 1; if (errs < 6) $display("FAULT_TREE_FAIL %0s src=%0d edge=%0d", what, s, e); end endtask
 task clear;
  begin @(posedge clk) #0.1 begin cfg_v = 1; cfg_target = 8'd125; end
   @(posedge clk) #0.1 begin cfg_v = 0; cfg_target = 0; end end endtask
 initial begin
  repeat (4) @(posedge clk); #0.1 rst_n = 1;
  repeat (40) @(posedge clk);
  if (!block_ready || die_fault) fail("idle", -1, 0);
  for (s = 0; s < NS; s = s + 1) begin
   // ---- pulse
   @(posedge clk) #0.1 src[s] = 1;
   @(posedge clk) #0.1 src[s] = 0; e = 1;
   while (e < lat[s]) begin if (die_fault) fail("early", s, e); @(posedge clk) #0.1 e = e + 1; end
   if (!die_fault) fail("not_at_latency", s, e);
   if (a_cause != (4'd1 << reg_of[s])) fail("cause", s, e);
   @(posedge clk) #0.1 if (block_ready) fail("block_ready_with_fault", s, e);
   repeat (120) @(posedge clk); #0.1 if (!die_fault || a_cause == 0) fail("not_sticky", s, e);
   clear; e = 1;
   repeat (4) @(posedge clk); #0.1 if (die_fault || a_cause != 0) fail("clear_late", s, e);
   for (e = 0; e < 3 * 64; e = e + 1) begin @(posedge clk) #0.1 if (die_fault || a_cause != 0) fail("stale_reset", s, e); end
   if (!block_ready) fail("block_ready_not_back", s, e);
   // ---- level held across a clear
   if (lvl[s]) begin
    nlev = nlev + 1;
    @(posedge clk) #0.1 src[s] = 1;
    repeat (lat[s] + 2) @(posedge clk); #0.1 if (!die_fault) fail("level_not_seen", s, 0);
    clear;
    repeat (8) @(posedge clk); #0.1 if (!die_fault) fail("level_not_reasserted", s, 0);
    #0.1 src[s] = 0; repeat (lat[s] + 4) @(posedge clk); clear; repeat (4) @(posedge clk);
    for (e = 0; e < 3 * 64; e = e + 1) begin @(posedge clk) #0.1 if (die_fault) fail("level_stale", s, e); end
   end
  end
  if (errs == 0) $display("FAULT_TREE PASS sources=%0d level_tests=%0d leaves=22", NS, nlev);
  else $display("FAULT_TREE_FAIL total=%0d", errs);
  $finish;
 end
endmodule
`default_nettype wire
''')
    open(out, 'w').write(''.join(L))
    print(f'tb: {NS} source bits, latency {min(lat)}..{max(lat)} edges')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1017)
