#!/bin/bash
# CLAUDE S81-RERUN: transaction bench of a forwarded-link station glue master (Icarus).  usage:
#   bench_stn.sh <pass|mut> <master> <work dir> [glue rtl]
# pass: 4,000 random words; every falling fi0 edge must present on do0 the di0 word sampled at that edge, and fo0 must
#       be ~fi0.  mut: the same on an ot_fwd_link_stage copy whose capture flips data bit 0 (must FAIL).
set -u
mode=$1; M=$2; O=$3; G=${4:-results/rtl/dsrom_s81_fulldie_20261004/r9m215/dsfd_glue.sv}
cd "$(dirname "$0")/../../.."; mkdir -p $O
S=rtl/common/ot_fwd_link_stage.sv
if [ $mode = mut ]; then sed 's/d<=i_d;/d<=i_d ^ 1;/' $S > $O/stage_mut.sv; cmp -s $O/stage_mut.sv $S && { echo 'mutant not applied'; exit 0; }; S=$O/stage_mut.sv; fi
W=$(grep -A3 "^module $M " $G | grep -o 'input wire \[[0-9]*:0\] di0' | grep -o '\[[0-9]*' | tr -d '[')
W=$((W + 1))
cat > $O/tb.sv <<EOT
module tb;
  reg fi = 0; reg [$W-1:0] di = 0; wire [$W-1:0] dq; wire fo; reg [$W-1:0] ex; integer i, err = 0;
  $M dut(.fi0(fi), .di0(di), .fo0(fo), .do0(dq));
  initial begin
    for (i = 0; i < 4000; i = i + 1) begin
      #1 di = {(($W + 31) / 32){\$random}};
      #4 fi = 1; #1 if (fo !== 1'b0) err = err + 1;
      #4 ex = di; fi = 0;
      #1 if (dq !== ex) err = err + 1; if (fo !== 1'b1) err = err + 1;
    end
    \$display("STN_BENCH %s %0d errors in %0d words (W=%0d)", err ? "FAIL" : "PASS", err, i, $W);
    \$finish;
  end
endmodule
EOT
iverilog -g2012 -o $O/tb.vvp -s tb $O/tb.sv $G $S || { echo BUILD_FAILED; exit 2; }
vvp -n $O/tb.vvp | tee $O/bench.log | grep STN_BENCH
grep -q 'STN_BENCH PASS' $O/bench.log
