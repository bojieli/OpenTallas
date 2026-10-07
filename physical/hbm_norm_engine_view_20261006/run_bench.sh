#!/bin/bash
# run_bench.sh <outdir> [mutant]  (cwd = repo root) exact bench of the pin-registered view against the DS1M golden row.
# mutant: flips one q_y bit on the output launch flop: the bench must report FAIL.
set -u; O=$1; M=${2:-}; mkdir -p $O; V=physical/hbm_norm_engine_view_20261006; G=results/rtl/hbm_norm_engine_view_20261006/gold
[ "$M" = corrupt ] && G=results/rtl/hbm_norm_engine_view_20261006/gold_corrupt
cp $V/ot_hbm_norm_engine_view.sv $O/view.sv
[ "$M" = mutant ] && sed -i 's/qy_o <= e_qy;/qy_o <= e_qy ^ {{1023{1'"'"'b0}},1'"'"'b1};/' $O/view.sv
[ "$M" = mutant ] && cmp -s $O/view.sv $V/ot_hbm_norm_engine_view.sv && { echo "mutant not applied"; exit 2; }
sed 's/ot_dsrom_su_norm #(.N(N), .D(D), .HC(HC), .RD(RD), .QUANT(QUANT), .RW(RW), .BW(BW), .RXS(RXS), .LA(LA), .SXC(SXC), .FREG(FREG)) dut (/ot_hbm_norm_engine_view dut (/' rtl/test/tb_dsrom_su_norm.sv > $O/tb.sv
grep -q "ot_hbm_norm_engine_view dut" $O/tb.sv || { echo "tb patch failed"; exit 2; }
srcs=$(grep -v norm_engine_view $V/sources.f | sed 's/^/ /' | tr -d '\n'); 
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_dsrom_su_norm -GN=64 -GD=5120 -GHC=1 -GRD=0 -GQUANT=1 -Mdir $O/obj $srcs $O/view.sv $O/tb.sv --build-jobs 4 > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -n 5 $O/build.log; exit 3; }
mkdir -p $O/run; cp $G/*.mem $O/run/; (cd $O/run && ../obj/Vtb_dsrom_su_norm > ../run.log 2>&1); grep -E "^SUN|^PASS|^FAIL" $O/run.log
grep -q '^PASS' $O/run.log
