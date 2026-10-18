#!/bin/bash
# RTL-BUILD-KV/PVTRUNK 10-18: unit bench of the PV result-trunk leaves (Verilator 5.050).
# usage: bench_pvr.sh <pass|mut> <qkd_pvr_inj|qkd_pvr_exit> <work dir>
# inj : 20,000 cycles of random pass words (random valid) + random y / y_valid events on both inject sides with random
#       compiled delays; every cycle b must equal: {id, 1, y} on cycle n + 3 + dl after a y_valid in cycle n, else the
#       previous cycle's a (one register stage).  Inject slots are drawn so the two sides never coincide.
# exit: random trunk words + epoch changes; p_* = previous cycle's t, p_epoch = the epoch sampled with beat 0, held.
# mut : the OT_QKD_PVR_MUT build (inj: side a one edge early; exit: no beat-0 latch) -- must FAIL.
set -u
mode=$1; M=$2; O=$3
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d $HOME/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
if [ "$M" = qkd_pvr_inj ]; then cat > "$O/tb.sv" <<'EOT'
module tb;
  reg ck = 0, rst_n = 0; always #5 ck = ~ck;
  reg [517:0] a = 0; reg [511:0] ya = 0, yb = 0; reg yva = 0, yvb = 0; reg [4:0] ida = 5'd3, idb = 5'd17;
  reg [7:0] dla = 0, dlb = 0; wire [517:0] b;
  qkd_pvr_inj #(.DW(8)) dut(.ck(ck), .rst_n(rst_n), .a(a), .ya(ya), .yb(yb), .yva(yva), .yvb(yvb), .ida(ida), .idb(idb),
                            .dla(dla), .dlb(dlb), .b(b));
  reg [517:0] ex [0:20400]; reg st [0:20400]; integer n, err = 0, inj = 0, k, ta = -1000, tb_ = -1000, sa = -1, sb = -1;
  initial begin
    for (n = 0; n <= 20400; n = n + 1) begin ex[n] = 0; st[n] = 0; end   // st = slot already scheduled (2-state safe)
    repeat (3) @(posedge ck); rst_n = 1; repeat (4) @(posedge ck);
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck);
      // cycle n: drive a, maybe a y_valid event (cycle n -> inject visible in cycle n + 3 + dl)
      for (k = 0; k < 518; k = k + 1) a[k] = $urandom;
      yva = 0; yvb = 0;
      if (n > 300 && n < 19600 && n > ta + 300 && ($urandom % 37) == 0) begin
        dla = $urandom % 200; for (k = 0; k < 512; k = k + 1) ya[k] = $urandom; yva = 1; ta = n; sa = n + 3 + dla;
        if (tb_ >= 0 && sa == sb) begin dla = dla + 1; sa = sa + 1; end
      end else if (n > 300 && n < 19600 && n > tb_ + 300 && ($urandom % 41) == 0) begin
        dlb = $urandom % 200; for (k = 0; k < 512; k = k + 1) yb[k] = $urandom; yvb = 1; tb_ = n; sb = n + 3 + dlb;
        if (ta >= 0 && sb == sa) begin dlb = dlb + 1; sb = sb + 1; end
      end
      if (!st[n + 1]) begin ex[n + 1] = a; st[n + 1] = 1; end
      if (yva) begin ex[sa] = {ida, 1'b1, ya}; st[sa] = 1; end
      if (yvb) begin ex[sb] = {idb, 1'b1, yb}; st[sb] = 1; end
      if (yva || yvb) inj = inj + 1;
      if (n > 1 && b !== ex[n]) begin if (err < 5) $display("cycle %0d: b %h want %h", n, b[517:500], ex[n][517:500]); err = err + 1; end
    end
    $display("PVR_BENCH %s %0d errors in %0d cycles, %0d injects (qkd_pvr_inj)", err ? "FAIL" : "PASS", err, n, inj);
    $finish;
  end
endmodule
EOT
else cat > "$O/tb.sv" <<'EOT'
module tb;
  reg ck = 0, rst_n = 0; always #5 ck = ~ck;
  reg [517:0] t = 0; reg [15:0] epoch = 0; wire p_valid; wire [4:0] p_beat; wire [15:0] p_epoch; wire [511:0] p_data;
  qkd_pvr_exit dut(.ck(ck), .rst_n(rst_n), .t(t), .epoch(epoch), .p_valid(p_valid), .p_beat(p_beat), .p_epoch(p_epoch), .p_data(p_data));
  reg [517:0] pt; reg [15:0] eh = 0, pe; integer n, err = 0, k, b = 0, beats = 0;
  initial begin
    repeat (3) @(posedge ck); rst_n = 1; repeat (4) @(posedge ck);
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck);
      if (n > 1 && (p_valid !== pt[512] || (pt[512] && (p_beat !== pt[517:513] || p_data !== pt[511:0] || p_epoch !== pe)))) begin
        if (err < 5) $display("cycle %0d: p %b %0d %0d want %b %0d %0d", n, p_valid, p_beat, p_epoch, pt[512], pt[517:513], pe);
        err = err + 1;
      end
      // a command = 32 consecutive beats; the epoch input changes at random times (a later start) mid-stream
      for (k = 0; k < 512; k = k + 1) t[k] = $urandom;
      if (b > 0 || ($urandom % 50) == 0) begin t[512] = 1; t[517:513] = b[4:0]; b = (b + 1) % 32; end
      else begin t[512] = 0; t[517:513] = $urandom; end
      if (($urandom % 13) == 0) epoch = $urandom;
      if (t[512] && t[517:513] == 0) eh = epoch;
      pt = t; pe = eh; if (t[512]) beats = beats + 1;
    end
    $display("PVR_BENCH %s %0d errors in %0d cycles, %0d beats (qkd_pvr_exit)", err ? "FAIL" : "PASS", err, n, beats);
    $finish;
  end
endmodule
EOT
fi
DEF=""; [ "$mode" = mut ] && DEF="-DOT_QKD_PVR_MUT"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/qwen_sys/kv_rly_std_20261016/qkd_pvr_trunk.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E "PVR_BENCH|cycle"
grep -q 'PVR_BENCH PASS' "$O/bench.log"
