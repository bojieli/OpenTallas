#!/bin/bash
# CLAUDE S81-RERUN: transaction bench of the column FIFO glue master dsfd_cfifo (ot_meso_fifo W564 crossing from the
# forwarded x clock xf to the column clock ck; Verilator --timing).  usage: bench_cfifo.sh <pass|mut> <work dir> [glue rtl]
# pass: 5 static phases of xf against ck; after the reset handshake 3,000 random words are written whenever the
#       writer has a credit; every word must leave on {xa, xb, cc} once, in order, with xs_v (xa[282]) set, the
#       go / cfg_go bits (cc[1:0]) qualified by valid, and the status word's fault bit (rd[69]) never set.
# mut : the same with xb taken one bit off (xq[549:284]): must FAIL.
set -u
mode=$1; O=$2; G=${3:-results/rtl/dsrom_s81_fulldie_20261004/r9m215/dsfd_glue.sv}
cd "$(dirname "$0")/../../.."; mkdir -p $O
if [ $mode = mut ]; then sed 's/xb = xq\[548:283\];/xb = xq[549:284];/; s/xb_r <= xq\[548:283\];/xb_r <= xq[549:284];/' $G > $O/glue_mut.sv; cmp -s $O/glue_mut.sv $G && { echo 'mutant not applied'; exit 0; }; G=$O/glue_mut.sv; fi
cat > $O/tb.sv <<'EOT'
`timescale 1ps/1ps
module tb;
  parameter real PH = 0.0;
  reg ck = 0, xf = 0, rst = 0; reg [565:0] xd = 0; reg [1:0] st = 0; reg [65:0] ri = 0;
  wire [282:0] xa; wire [265:0] xb; wire [14:0] cc; wire [69:0] rd; wire co, rf, rs;
  dsfd_cfifo dut(.cc(cc), .ck(ck), .co(co), .rd(rd), .rf(rf), .ri(ri), .rs(rs), .rst(rst), .st(st), .xa(xa), .xb(xb), .xd(xd), .xf(xf));
  always #416 ck = ~ck;
  initial begin #(PH); forever #416 xf = ~xf; end
  reg [563:0] sent [0:4095]; integer ns = 0, nr = 0, err = 0, cyc = 0; reg [563:0] w, e;
  initial begin rst = 1; xd[0] = 0; #100 rst = 0; #20000 rst = 1; #8000 xd[0] = 1; end   // a real falling edge: async resets fire
  always @(posedge xf) begin
    cyc <= cyc + 1;
    xd[1] <= 0;
    if (xd[0] && dut.wr && ns < 3000 && ($random & 3) != 0) begin
      w = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random,
           $random, $random, $random, $random, $random, $random}; w[282] = 1'b1;
      sent[ns] = w; ns = ns + 1; xd[565:2] <= w; xd[1] <= 1;
    end
  end
  always @(posedge ck) if (rs) begin
    if (rd[69]) err = err + 1;
    if (xa[282]) begin
      e = sent[nr];
      if (xa[281:0] !== e[281:0] || xb !== e[548:283] || cc[14:2] !== e[563:551] || cc[1:0] !== e[550:549]) begin
        if (err < 3) $display("ERROR word %0d", nr); err = err + 1; end
      nr = nr + 1;
    end else if (cc[1:0] !== 2'b00) err = err + 1;
  end
  initial begin
    #6000000;
    if (nr != ns || ns < 2000) err = err + 1;
    $display("CFIFO_BENCH %s phase %0d ps: %0d sent, %0d received, %0d errors", err ? "FAIL" : "PASS", PH, ns, nr, err);
    $finish;
  end
endmodule
EOT
S="rtl/common/ot_meso_fifo.sv rtl/common/ot_fwd_link_stage.sv rtl/common/ot_ratio_cdc_fifo.sv rtl/v41die/ot_v41_retn_w17w10.sv rtl/v41rom/ot_v41_ret.sv"
# Verilator (2-state, random initial values): the meso ring counter is never reset by design, so a 4-state simulator
# keeps it X forever (Icarus) -- the same reason tools/meso_fifo_campaign.py runs Verilator
fail=0
for ph in 10 200 416 600 820; do
  verilator --binary --timing -O1 --x-assign unique --x-initial unique -Wno-fatal -Wno-lint -Wno-style -GPH=$ph.0 \
    --top-module tb $O/tb.sv $G $S -Mdir $O/obj_$ph -o tb > $O/build_$ph.log 2>&1 || { echo BUILD_FAILED; tail -n 5 $O/build_$ph.log; exit 2; }
  $O/obj_$ph/tb +verilator+rand+reset+2 +verilator+seed+$ph > $O/run_$ph.log 2>&1
  grep CFIFO_BENCH $O/run_$ph.log || { echo "CFIFO_BENCH FAIL no verdict phase $ph"; fail=1; }
  grep -q 'CFIFO_BENCH PASS' $O/run_$ph.log || fail=1
done
exit $fail
