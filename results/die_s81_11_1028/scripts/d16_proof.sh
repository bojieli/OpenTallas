#!/bin/bash
# DIE-S81-11 (COORD 07:20 (2), 12.16 b(iii)): RTL proof that ot_dp_clk_landing_ca works at DEPTH 16, same Verilator
# bench as rtl/test/meso/ca/run_ca_bench.sh (unchanged sources).  Usage: d16_proof.sh REPO OUT
# (1) lag sweeps K in {-2,1,2,5} x DEPTH 16 over L = -33T..+33T at 2 ps: clean window must be [0.5, 15.5] T contiguous,
#     silent-wrong 0 (incl. the 1-bit lap alias at L - 32T); DEPTH 8 K=2 control at 2 ps.
# (2) mutants at DEPTH 16 (must be CAUGHT): NO_TAG, K, NO_GUARD.
# (3) strap form ot_dp_clk_landing_cas elaborates at DEPTH 16 (strap 8 bits) - verilator lint.
set -u
export HOME=/tmp CCACHE_DISABLE=1
repo=$1; out=$2; mkdir -p $out; cd $out
cp $repo/rtl/common/{ot_meso_fifo.sv,ot_dp_clk_landing.sv,ot_dp_clk_landing_ca.sv} $repo/rtl/test/meso/ca/tb_dp_clk_landing_ca.{sv,cpp} .
# D16 arms later (ARM = 2*DEPTH+4 = 36 cycles): the bench's 80-period horizon leaves < 40 checks at K=5, so the
# local copy runs 140 periods (bench-only change; RTL untouched)
sed -i 's/long tend = tr0 + 80 \* T;/long tend = tr0 + 140 * T;/' tb_dp_clk_landing_ca.cpp; grep -q "tr0 + 140 \* T" tb_dp_clk_landing_ca.cpp || { echo "horizon patch FAIL"; exit 2; }
V="verilator --cc --exe --build -j 4 -Wno-fatal -Wno-lint"
S="tb_dp_clk_landing_ca.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_dp_clk_landing_ca.cpp"
rc=0
run() { # K D range step [defines]
  K=$1; D=$2; R=$3; st=$4; shift 4; tag=k${K}_d${D}$(echo "$@" | tr -cd 'A-Z_')
  $V -CFLAGS "-DKPAR=$K -DDPAR=$D" -GK=$K -GDEPTH=$D "$@" --top-module tb_dp_clk_landing_ca $S --Mdir o_$tag > b_$tag.log 2>&1 || { echo "BUILD FAIL $tag"; return 2; }
  o_$tag/Vtb_dp_clk_landing_ca sweep $(( -R*833 )) $(( R*833 )) $st 2>/dev/null
}
for K in -2 1 2 5; do run $K 16 33 2 || rc=1; done
run 2 8 17 2 || rc=1
for M in NO_TAG K NO_GUARD; do
  run 2 16 33 3 -DOT_MESO_CA_MUTANT_$M > mut_$M.txt; r=$?
  if [ $r = 0 ]; then echo "MUTANT $M SURVIVED: $(cat mut_$M.txt)"; rc=1; elif [ $r = 2 ]; then echo "MUTANT $M BUILD FAIL"; rc=1; else echo "MUTANT $M CAUGHT: $(tail -1 mut_$M.txt)"; fi
done
cat > top_cas.sv <<'X'
module top_cas(input fclk, t_rst_n, clk, rst_n, input [7:0] strap_k, input [63:0] d, output [63:0] q, output ready, fault);
  ot_dp_clk_landing_cas #(.W(64), .DEPTH(16)) u (.*);
endmodule
X
verilator --lint-only -Wno-fatal -Wno-lint --top-module top_cas top_cas.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv > lint_cas.log 2>&1 && echo "CAS DEPTH16 elaboration OK" || { echo "CAS DEPTH16 elaboration FAIL"; rc=1; }
echo "RC $rc"; exit $rc
