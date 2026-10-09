#!/bin/bash
# S81-TAIL 2026-10-08: transaction bench of a common-clock hub station glue master (dsfd_hstnh_* / dsfd_hstnv_*, Icarus).
#   bench_hstn.sh <pass|mut> <master> <work dir> [glue rtl]
# pass: 4,000 random words; after every rising ck edge dq must equal the di word presented before that edge.
# mut: the same on an ot_fwd_link_stage copy whose capture flips data bit 0 (must FAIL).
set -u
mode=$1; M=$2; O=$3; G=${4:-physical/s81_die_views/hend/m221pq/dsfd_glue.sv}
cd "$(dirname "$0")/../../.."; mkdir -p $O
S=rtl/common/ot_fwd_link_stage.sv
if [ $mode = mut ]; then sed 's/d<=i_d;/d<=i_d ^ 1;/' $S > $O/stage_mut.sv; cmp -s $O/stage_mut.sv $S && { echo 'mutant not applied'; exit 0; }; S=$O/stage_mut.sv; fi
W=$(grep -A3 "^module $M " $G | grep -o 'input wire \[[0-9]*:0\] di' | grep -o '\[[0-9]*' | tr -d '[')
W=$((W + 1))
cat > $O/tb.sv <<EOT
module tb;
  reg ck = 0; reg [$W-1:0] di = 0; wire [$W-1:0] dq; reg [$W-1:0] ex; integer i, err = 0;
  $M dut(.ck(ck), .di(di), .dq(dq));
  initial begin
    for (i = 0; i < 4000; i = i + 1) begin
      #1 di = {(($W + 31) / 32){\$random}}; ex = di;
      #4 ck = 1;
      #1 if (dq !== ex) err = err + 1;
      #1 di = ~di;                 // a change after the edge must not reach dq before the next edge
      #2 if (dq !== ex) err = err + 1;
      #1 ck = 0;
    end
    \$display("STN_BENCH %s %0d errors in %0d words (W=%0d)", err ? "FAIL" : "PASS", err, i, $W);
    \$finish;
  end
endmodule
EOT
iverilog -g2012 -o $O/tb.vvp -s tb $O/tb.sv $G $S || { echo BUILD_FAILED; exit 2; }
vvp -n $O/tb.vvp | tee $O/bench.log | grep STN_BENCH
grep -q 'STN_BENCH PASS' $O/bench.log
