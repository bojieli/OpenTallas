#!/usr/bin/env bash
# HBM-CONS-2/SUK vK bench: same EXPX lock-step method as results/die_hbm_1106/sux/bench (old part-18 splitx vs the new core), T=15 S=9, side +9
set -u
S=/srv/opentallas-scratch3/claude/hbm-form-split-14-sux; D=/srv/opentallas-scratch3/claude/hbm-cons-2-suk
EB=/srv/opentallas-scratch3/claude/hbm-form-split-13-expx/benv; SH=$EB/bench/oc
RX=$S/repo/rtl/hbm_accel/cores_split/reform_1104a/lane_x; H=$S/repo/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11
V=$HOME/.local/opentallas-tools/bin/verilator; LEAF=$(sed "s#base/#$EB/base/#g" $EB/bench/leaf.txt)
G=$D/gen_xk; cd $D; mkdir -p bx/oc_k bx/oc_t14 bx/oc_s8 bx/src bf/o bf/o_s8 bf/src
python3 -I gen_lane_xk.py $S/repo $G $RX/ot_hbm_su_pg_lane_full_x_core.sv
sed 's/^module ot_hbm_su_pg_lane_exp_x_core #(/module ot_hbm_su_pg_lane_exp_x_core_vb #(/' $G/ot_hbm_su_pg_lane_exp_x_core.sv > bx/src/core_vd.sv
sed 's/^module ot_hbm_su_pg_lane_full_x_core #(/module ot_hbm_su_pg_lane_full_x_core_vb #(/' $G/ot_hbm_su_pg_lane_full_x_core.sv > bf/src/core_vd.sv
EQ=$S/repo/results/die_hbm_1106/expx_vc/bench/eq_xc.py; SX=$RX/ot_hbm_su_pg_lane_exp_core__splitx.sv; MK=$S/repo/results/die_hbm_1106/sux/mk_bench_fx.py
python3 -I $EQ $SX bx/oc_k/tb.sv 40 77 15 9; python3 -I $EQ $SX bx/oc_t14/tb.sv 40 77 14 9; python3 -I $EQ $SX bx/oc_s8/tb.sv 40 77 15 8
python3 -I $MK $SH bx/oc_k/tb.sv bf/o 9; python3 -I $MK $SH bx/oc_s8/tb.sv bf/o_s8 9
runx() { O=$1; M=$2; T=bx/$O/obj_m$M
  prlimit --as=24000000000 $V --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir $T -o sim bx/$O/tb.sv $RX/ot_hbm_su_pg_lane_exp_core__splitx.sv $SH/splitx_vb.sv $SH/x_old__fs.sv $SH/x_new__fs.sv $SH/s__fs.sv $RX/ot_hbm_su_pg_lane_exp_x_core.sv $RX/ot_hbm_su_static_lane_x.sv $RX/ot_hbm_su_static_lane_pinreg_x.sv bx/src/core_vd.sv $G/ot_hbm_su_static_lane_xb.sv $G/ot_hbm_su_static_lane_pinreg_xb.sv $RX/ot_hbm_su_pg_sfu_s_core.sv $LEAF $H/sram_bench_model.sv > bx/$O/build_m$M.log 2>&1 || { echo "BUILD FAIL exp $O $M"; tail -20 bx/$O/build_m$M.log | cut -c1-300; return; }
  $T/sim > bx/$O/sim_m$M.log 2>&1; echo "exp $O MUT $M: $(grep XEQ bx/$O/sim_m$M.log)"; grep MISMATCH bx/$O/sim_m$M.log | head -3 | cut -c1-140; rm -rf $T; }
runf() { O=$1; M=$2; DD=$3; T=bf/$O/obj_m${M}d$DD
  prlimit --as=24000000000 $V --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M -DOT_SIDE_D=$DD --top-module tb -Mdir $T -o sim bf/$O/tbf.sv $RX/ot_hbm_su_pg_lane_full_core__splitx.sv bf/$O/splitf_vb.sv bf/$O/xf_old__fs.sv bf/$O/xf_new__fs.sv $SH/s__fs.sv $RX/ot_hbm_su_pg_lane_full_x_core.sv $RX/ot_hbm_su_static_lane_x.sv $RX/ot_hbm_su_static_lane_pinreg_x.sv bf/src/core_vd.sv $G/ot_hbm_su_static_lane_xb.sv $G/ot_hbm_su_static_lane_pinreg_xb.sv $RX/ot_hbm_su_pg_sfu_s_core.sv $LEAF $H/sram_bench_model.sv > bf/$O/build_m${M}d$DD.log 2>&1 || { echo "BUILD FAIL full $O $M $DD"; tail -20 bf/$O/build_m${M}d$DD.log | cut -c1-300; return; }
  $T/sim > bf/$O/sim_m${M}d$DD.log 2>&1; echo "full $O MUT $M SIDE_D $DD: $(grep XEQ bf/$O/sim_m${M}d$DD.log)"; grep MISMATCH bf/$O/sim_m${M}d$DD.log | head -3 | cut -c1-140; rm -rf $T; }
( runx oc_k 0; runf o 0 8; runf o 0 7 ) &
( for m in 1 2 3; do runx oc_k $m; done; runx oc_t14 0 ) &
( for m in 4 5 6; do runx oc_k $m; done; runx oc_s8 0 ) &
( runf o 1 8; runf o 3 8; runf o 6 8; runf o_s8 0 8 ) &
wait; echo BENCH_DONE $(date)
