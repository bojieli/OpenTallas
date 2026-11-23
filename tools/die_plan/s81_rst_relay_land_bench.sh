#!/bin/bash
# S81-RST-RELAY-LAND equivalence bench: the LANDED ot_rst_relay (overlay + define) vs rtl/lib/ot_rst_relay_l.sv and vs the
# unpatched ot_rst_relay, lock-step, random asynchronous rst_n_in, REGIONS 4/20 x TREE_STAGES 1/2.  A mutant (relay clear from
# sync_q[0], D 1: release one edge early) must FAIL; relay D from sync_q[0] alone is equivalent (the clear holds it).   bash tools/die_plan/s81_rst_relay_land_bench.sh [WORKDIR]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); W=${1:-$(mktemp -d)}; mkdir -p "$W"
cp "$ROOT/rtl/lib/ot_rst_relay.sv" "$W/land.sv"; python3 -I "$ROOT/tools/die_plan/s81_rst_relay_land_overlay.py" "$W/land.sv" >/dev/null
sed -e 's/module ot_rst_relay #/module rr_land #/' "$W/land.sv" > "$W/rr_land.sv"
sed -e 's/module ot_rst_relay #/module rr_src #/' "$ROOT/rtl/lib/ot_rst_relay.sv" > "$W/rr_src.sv"
sed -e 's/OT_RST_RELAY_LANDED sync_q\[SYNC_STAGES-1\]/OT_RST_RELAY_LANDED sync_q[0]/' \
    -e 's/relay_q\[t\] <= {REGIONS{sync_q\[SYNC_STAGES-1\]}};/relay_q[t] <= {REGIONS{rst_n_in | sync_q[0]}};/' \
    -e 's/module rr_land #/module rr_mut #/' "$W/rr_land.sv" > "$W/rr_mut.sv"
grep -qF 'LANDED sync_q[0]' "$W/rr_mut.sv"; grep -qF '{REGIONS{rst_n_in | sync_q[0]}}' "$W/rr_mut.sv"
cat > "$W/tb.sv" <<'TB'
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n_in = 0; integer i, bad = 0, badm = 0, cmp = 0; reg mut_seen;
  always #1 clk = ~clk;
`define DUT(R,T) \
  wire [R-1:0] l_``R``_``T, s_``R``_``T, r_``R``_``T, m_``R``_``T; \
  rr_land #(.REGIONS(R), .TREE_STAGES(T)) ul_``R``_``T (.clk(clk), .rst_n_in(rst_n_in), .rst_n(l_``R``_``T)); \
  rr_src  #(.REGIONS(R), .TREE_STAGES(T)) us_``R``_``T (.clk(clk), .rst_n_in(rst_n_in), .rst_n(s_``R``_``T)); \
  ot_rst_relay_l #(.REGIONS(R), .TREE_STAGES(T)) ur_``R``_``T (.clk(clk), .rst_n_in(rst_n_in), .rst_n(r_``R``_``T)); \
  rr_mut  #(.REGIONS(R), .TREE_STAGES(T)) um_``R``_``T (.clk(clk), .rst_n_in(rst_n_in), .rst_n(m_``R``_``T));
  `DUT(4,1) `DUT(4,2) `DUT(20,1) `DUT(20,2)
  wire [47:0] L = {l_4_1, l_4_2, l_20_1, l_20_2}, S = {s_4_1, s_4_2, s_20_1, s_20_2},
              Q = {r_4_1, r_4_2, r_20_1, r_20_2}, M = {m_4_1, m_4_2, m_20_1, m_20_2};
  task chk; begin cmp = cmp + 1; if (L !== S || L !== Q) bad = bad + 1; if (M !== L) badm = badm + 1; end endtask
  always @(clk or rst_n_in) #0.01 chk;
  initial begin
    #3.3 rst_n_in = 1;
    for (i = 0; i < 4000; i = i + 1) begin
      #(($urandom % 23) + 0.37);
      if (($urandom % 5) == 0) rst_n_in = ~rst_n_in; else if (($urandom % 9) == 0) begin rst_n_in = 0; #0.4 rst_n_in = 1; end
    end
    $display("RRL_BENCH compares=%0d land_vs_src_and_l_mismatch=%0d mutant_mismatch=%0d", cmp, bad, badm);
    if (bad == 0 && badm > 0) $display("RRL_BENCH PASS"); else $display("RRL_BENCH FAIL");
    $finish;
  end
endmodule
TB
iverilog -g2012 -DOT_RST_RELAY_LANDED -o "$W/sim" "$W/tb.sv" "$W/rr_land.sv" "$W/rr_src.sv" "$W/rr_mut.sv" "$ROOT/rtl/lib/ot_rst_relay_l.sv"
vvp -n "$W/sim" | tee "$W/bench.log" | grep RRL_BENCH
grep -q "RRL_BENCH PASS" "$W/bench.log"
