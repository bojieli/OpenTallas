#!/usr/bin/env bash
# run.sh MUTS... : build + run the vB lock-step bench per mutant (0 must PASS, others FAIL)
cd "${EXPX_DIR:?set EXPX_DIR to the lane dir}"
RX=wt/rtl/hbm_accel/cores_split/reform_1104a/lane_x; H=wt/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11; O=bench/o
V=$HOME/.local/opentallas-tools/bin/verilator; LEAF=$(cat bench/leaf.txt)
for M in "$@"; do
  rm -rf $O/obj_m$M
  prlimit --as=24000000000 $V --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir $O/obj_m$M -o sim     $O/tb.sv $RX/ot_hbm_su_pg_lane_exp_core__splitx.sv $O/splitx_vb.sv $O/x_old__fs.sv $O/x_new__fs.sv $O/s__fs.sv     $RX/ot_hbm_su_pg_lane_exp_x_core.sv $RX/ot_hbm_su_static_lane_x.sv $RX/ot_hbm_su_static_lane_pinreg_x.sv     bench/src_new/core_vb.sv gen1/ot_hbm_su_static_lane_xb.sv gen1/ot_hbm_su_static_lane_pinreg_xb.sv     $RX/ot_hbm_su_pg_sfu_s_core.sv $LEAF $H/sram_bench_model.sv > $O/build_m$M.log 2>&1 || { echo BUILD FAIL $M; tail -20 $O/build_m$M.log | cut -c1-300; continue; }
  $O/obj_m$M/sim > $O/sim_m$M.log 2>&1; echo "MUT $M: $(grep XEQ $O/sim_m$M.log)"; grep MISMATCH $O/sim_m$M.log | head -4 | cut -c1-140
  rm -rf $O/obj_m$M
done
