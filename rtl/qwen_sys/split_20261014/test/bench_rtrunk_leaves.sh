#!/bin/bash
# KV-RTRUNK 10-17: bit-exact bench of the PV pair result-trunk leaves (Verilator 5.050), rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv.
# usage: bench_rtrunk_leaves.sh <pass|mut|smut|nopr> <qkd_rlyi_258|qkd_pv_rs_hd|qkd_rlyi_258s|qkd_pv_rs_hd_r|qkd_pv_rs_hd_f> <work dir>
#  KV-KITS/NATIVE 10-18 successors: qkd_rlyi_258s (select registered at its pin: b must equal (s_r ? y : a) of the previous
#  cycle, s_r = s one cycle earlier; smut = the r1 unregistered select, must FAIL); qkd_pv_rs_hd_r (T0 V / T copies driven
#  equal to a<q>[256] / a<q>[257] as the generator wires them; same model as qkd_pv_rs_hd).
#  AD3-KV-RSHD 10-18: qkd_pv_rs_hd_f (half-local selects): stimulus also holds the generator's T0 part invariant
#  a1[256] == a0[256], a1[257] == a0[257] (both parts' V / T come from the same signals), copies equal; same model.
#  HKV-PVRS2 10-19 rev f2 (input pin registers): the same model ONE EDGE LATER (it reads the previous edge's pins);
#  nopr = the OT_QKD_RSHD_NOPR build (the f1 one-stage leaf, input registers bypassed) -- must FAIL.
#  qkd_rlyi_258: 20,000 random cycles; b must equal the previous cycle's (s ? y : a) on every bit.
#  qkd_pv_rs_hd: 20,000 random cycles (T0 / T1 valid never both set, as scheduled); the beat word must equal the model.
#  mut: the OT_QKD_RLYI_MUT build (inject bit 0 inverted) / header with T0's halves swapped (OT_QKD_RSHD_MUT) -- must FAIL.
set -u
mode=$1; M=$2; O=$3
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
if [ "$M" = qkd_rlyi_258s ]; then
cat > "$O/tb.sv" <<'EOT'
module tb;
  reg ck = 0; reg s = 0; reg [257:0] a = 0, y = 0; wire [257:0] b; reg [257:0] ex = 0; reg sr = 0;
  integer n = 0, err = 0;
  qkd_rlyi_258s dut(.ck(ck), .s(s), .a(a), .y(y), .b(b));
  always #5 ck = ~ck;
  initial begin
    @(posedge ck); ex = sr ? y : a; sr = s;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck); if (n > 0 && b !== ex) err = err + 1;
      for (int k = 0; k < 258; k++) begin a[k] = $urandom; y[k] = $urandom; end
      s = $urandom;
      @(posedge ck); ex = sr ? y : a; sr = s;
    end
    $display("RTRUNK_LEAF %s %0d errors in %0d cycles (qkd_rlyi_258s)", err ? "FAIL" : "PASS", err, n);
    $finish;
  end
endmodule
EOT
elif [ "$M" = qkd_rlyi_258 ]; then
cat > "$O/tb.sv" <<'EOT'
module tb;
  reg ck = 0; reg s = 0; reg [257:0] a = 0, y = 0; wire [257:0] b; reg [257:0] ex = 0;
  integer n = 0, err = 0;
  qkd_rlyi_258 dut(.ck(ck), .s(s), .a(a), .y(y), .b(b));
  always #5 ck = ~ck;
  initial begin
    @(posedge ck); ex = s ? y : a;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck); if (b !== ex) err = err + 1;
      for (int k = 0; k < 258; k++) begin a[k] = $urandom; y[k] = $urandom; end
      s = $urandom;
      @(posedge ck); ex = s ? y : a;
    end
    $display("RTRUNK_LEAF %s %0d errors in %0d cycles (qkd_rlyi_258)", err ? "FAIL" : "PASS", err, n);
    $finish;
  end
endmodule
EOT
else
cat > "$O/tb.sv" <<'EOT'
module tb;
  reg ck = 0; reg [257:0] a0 = 0, a1 = 0, b0 = 0, b1 = 0; reg [15:0] ep = 0;
  wire ov; wire [4:0] ob; wire [15:0] oe; wire [511:0] od;
  reg [4:0] cnt = 0; reg [15:0] er = 0; reg xv; reg [4:0] xb; reg [15:0] xe; reg [511:0] xd;
  integer n = 0, err = 0, started = 0;
`ifdef OT_RSHD_F
  qkd_pv_rs_hd_f dut(.ck(ck), .a0(a0), .a1(a1), .a0v({31{a0[256]}}), .a1v({31{a1[256]}}), .a0t(a0[257]), .a1t(a1[257]),
                     .b0(b0), .b1(b1), .ep(ep), .o_valid(ov), .o_beat(ob), .o_epoch(oe), .o_data(od));
`elsif OT_RSHD_R
  qkd_pv_rs_hd_r dut(.ck(ck), .a0(a0), .a1(a1), .a0v({31{a0[256]}}), .a1v({31{a1[256]}}), .a0t(a0[257]), .a1t(a1[257]),
                     .b0(b0), .b1(b1), .ep(ep), .o_valid(ov), .o_beat(ob), .o_epoch(oe), .o_data(od));
`else
  qkd_pv_rs_hd dut(.ck(ck), .a0(a0), .a1(a1), .b0(b0), .b1(b1), .ep(ep), .o_valid(ov), .o_beat(ob), .o_epoch(oe), .o_data(od));
`endif
  always #5 ck = ~ck;
  // the model's inputs: this cycle's pins, or (qkd_pv_rs_hd_f rev f2, input pin registers) the previous edge's pins
  reg [257:0] m0, m1, n0, n1, p0 = 0, p1 = 0, q0 = 0, q1 = 0; reg [15:0] me, pe = 0;
  task automatic take;
`ifdef OT_RSHD_F
    m0 = p0; m1 = p1; n0 = q0; n1 = q1; me = pe; p0 = a0; p1 = a1; q0 = b0; q1 = b1; pe = ep;
`else
    m0 = a0; m1 = a1; n0 = b0; n1 = b1; me = ep;
`endif
  endtask
  task automatic model; reg t, va, vb;
    take;
    t = m0[257] & m1[257]; va = m0[256] & m1[256]; vb = n0[256] & n1[256];
    xv = va | vb; xb = t ? 5'd0 : cnt; xe = t ? me : er; xd = va ? {m1[255:0], m0[255:0]} : {n1[255:0], n0[255:0]};
    if (t) started = 1;
    cnt = t ? 5'd1 : cnt + 5'd1; er = t ? me : er;
  endtask
  initial begin
    a0[257] = 1; a1[257] = 1;
    @(posedge ck); model;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge ck); if (ov !== xv || od !== xd || (started && (ob !== xb || oe !== xe))) err = err + 1;
      for (int k = 0; k < 256; k++) begin a0[k] = $urandom; a1[k] = $urandom; b0[k] = $urandom; b1[k] = $urandom; end
      ep = $urandom; a0[257] = ($urandom % 7) == 0; a1[257] = a0[257] | ($urandom % 2);
      a0[256] = $urandom; a1[256] = $urandom; b0[256] = $urandom; b1[256] = $urandom;
`ifdef OT_RSHD_F
      a1[256] = a0[256]; a1[257] = a0[257];
`endif
      if (a0[256] & a1[256]) begin b0[256] = 0; end
      b0[257] = $urandom; b1[257] = $urandom;
      @(posedge ck); model;
    end
`ifdef OT_RSHD_F
    $display("RTRUNK_LEAF %s %0d errors in %0d cycles (qkd_pv_rs_hd_f)", err ? "FAIL" : "PASS", err, n);
`elsif OT_RSHD_R
    $display("RTRUNK_LEAF %s %0d errors in %0d cycles (qkd_pv_rs_hd_r)", err ? "FAIL" : "PASS", err, n);
`else
    $display("RTRUNK_LEAF %s %0d errors in %0d cycles (qkd_pv_rs_hd)", err ? "FAIL" : "PASS", err, n);
`endif
    $finish;
  end
endmodule
EOT
fi
DEF=""; [ "$mode" = mut ] && DEF="-DOT_QKD_RLYI_MUT -DOT_QKD_RSHD_MUT"; [ "$mode" = smut ] && DEF="-DOT_QKD_RLYI_SMUT"
[ "$mode" = nopr ] && DEF="-DOT_QKD_RSHD_NOPR"
[ "$M" = qkd_pv_rs_hd_r ] && DEF="$DEF -DOT_RSHD_R"
[ "$M" = qkd_pv_rs_hd_f ] && DEF="$DEF -DOT_RSHD_F"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RTRUNK_LEAF
grep -q 'RTRUNK_LEAF PASS' "$O/bench.log"
