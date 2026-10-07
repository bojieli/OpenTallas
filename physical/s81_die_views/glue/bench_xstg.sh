#!/bin/bash
# CLAUDE S81-RERUN v8: transaction bench of the crossing stage dsfd_xstg_515 (Icarus).  usage:
#   bench_xstg.sh <pass|mut> <work dir> <glue rtl>
# cw and ck at the same period with a static phase offset (0, +-320 ps of 833 ps, i.e. within the 385 ps bound);
# 3,000 random valid words in, in order and exact out (lane vr: bit 0 rst_n, bit 1 valid).  mut: the meso FIFO with its
# read pointer advanced by one slot (must FAIL).
set -u
mode=$1; O=$2; G=$3
cd "$(dirname "$0")/../../.."; mkdir -p $O
S=rtl/common/ot_meso_fifo.sv
if [ $mode = mut ]; then sed 's/\.OFFSET(4)/.OFFSET(3)/' $G > $O/glue_mut.sv; cmp -s $O/glue_mut.sv $G && { echo 'mutant not applied'; exit 0; }; G=$O/glue_mut.sv; fi
for PH in 0 320 513; do
cat > $O/tb_$PH.sv <<EOT
\`timescale 1ps/1ps
module tb;
  reg cw = 0, ck = 0; reg [514:0] i = 0; wire [514:0] o;
  always #416.5 cw = ~cw;
  initial begin #$PH; forever #416.5 ck = ~ck; end
  dsfd_xstg_515 dut(.cw(cw), .ck(ck), .i(i), .o(o));
  reg [512:0] q [0:4095]; integer wp = 0, rp = 0, err = 0, n;
  initial begin
    repeat (20) @(posedge cw); i[0] = 1;
    repeat (60) @(posedge cw);
    for (n = 0; n < 3000; n = n + 1) begin
      @(posedge cw); #1 i[1] = (\$random % 4) != 0;
      i[514:2] = {17{\$random}};
      if (i[1]) begin q[wp % 4096] = i[514:2]; wp = wp + 1; end
    end
    @(posedge cw); #1 i[1] = 0;
    repeat (80) @(posedge ck);
    \$display("XSTG_BENCH %s ph=$PH err=%0d in=%0d out=%0d", (err == 0 && rp == wp) ? "PASS" : "FAIL", err, wp, rp);
    \$finish;
  end
  always @(posedge ck) #2 if (o[1] && o[0]) begin
    if (o[514:2] !== q[rp % 4096]) err = err + 1;
    rp = rp + 1;
  end
endmodule
EOT
iverilog -g2012 -o $O/tb_$PH.vvp -s tb $O/tb_$PH.sv $G $S rtl/common/ot_fwd_link_stage.sv 2> $O/build_$PH.log || { echo BUILD_FAILED; cat $O/build_$PH.log | head; exit 2; }
vvp -n $O/tb_$PH.vvp | tee $O/bench_$PH.log | grep XSTG_BENCH
done
! grep -q 'XSTG_BENCH FAIL' $O/bench_*.log && [ $(grep -c 'XSTG_BENCH PASS' $O/bench_*.log | awk -F: '{s+=$2} END {print s}') -eq 3 ]
