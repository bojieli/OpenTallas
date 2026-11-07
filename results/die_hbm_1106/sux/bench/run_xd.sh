#!/usr/bin/env bash
# run_xd.sh TBDIR MUTS... : exp_x vB(xd) lock-step bench (old part-18 splitx exp_x vs gen_lane_xd exp_x, EXPX method):
# TBDIR holds tb.sv from eq_xc.py with T/S (oc_d: T=14 S=8 must PASS at MUT 0; oc_t13 / oc_s7 controls must FAIL)
S=/srv/opentallas-scratch3/claude/hbm-form-split-14-sux; cd $S/bx
EB=/srv/opentallas-scratch3/claude/hbm-form-split-13-expx/benv
RX=$S/repo/rtl/hbm_accel/cores_split/reform_1104a/lane_x; H=$S/repo/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11
O=$1; shift; SH=$EB/bench/oc
V=$HOME/.local/opentallas-tools/bin/verilator; LEAF=$(sed "s#base/#$EB/base/#g" $EB/bench/leaf.txt)
for M in "$@"; do
  rm -rf $O/obj_m$M
  prlimit --as=24000000000 $V --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir $O/obj_m$M -o sim $O/tb.sv $RX/ot_hbm_su_pg_lane_exp_core__splitx.sv $SH/splitx_vb.sv $SH/x_old__fs.sv $SH/x_new__fs.sv $SH/s__fs.sv $RX/ot_hbm_su_pg_lane_exp_x_core.sv $RX/ot_hbm_su_static_lane_x.sv $RX/ot_hbm_su_static_lane_pinreg_x.sv src/core_vd.sv $S/gen_xd/ot_hbm_su_static_lane_xb.sv $S/gen_xd/ot_hbm_su_static_lane_pinreg_xb.sv $RX/ot_hbm_su_pg_sfu_s_core.sv $LEAF $H/sram_bench_model.sv > $O/build_m$M.log 2>&1 || { echo BUILD FAIL $M; tail -20 $O/build_m$M.log | cut -c1-300; continue; }
  $O/obj_m$M/sim > $O/sim_m$M.log 2>&1; echo "$O MUT $M: $(grep XEQ $O/sim_m$M.log)"; grep MISMATCH $O/sim_m$M.log | head -3 | cut -c1-140
  rm -rf $O/obj_m$M
done
