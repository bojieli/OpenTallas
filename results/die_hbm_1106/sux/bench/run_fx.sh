#!/usr/bin/env bash
# run_fx.sh TBDIR MUT[:SIDE_D]... : full_x vB(xd) lock-step bench (old part-18 splitx full_x vs gen_lane_xd full_x); SIDE_D 7 = +8 (correct)
S=/srv/opentallas-scratch3/claude/hbm-form-split-14-sux; cd $S/bf
EB=/srv/opentallas-scratch3/claude/hbm-form-split-13-expx/benv
RX=$S/repo/rtl/hbm_accel/cores_split/reform_1104a/lane_x; H=$S/repo/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11
O=$1; shift
V=$HOME/.local/opentallas-tools/bin/verilator; LEAF=$(sed "s#base/#$EB/base/#g" $EB/bench/leaf.txt)
for A in "$@"; do
  M=${A%%:*}; D=7; [ "$A" != "$M" ] && D=${A#*:}
  T=m${M}d$D; rm -rf $O/obj_$T
  prlimit --as=24000000000 $V --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M -DOT_SIDE_D=$D --top-module tb -Mdir $O/obj_$T -o sim $O/tbf.sv $RX/ot_hbm_su_pg_lane_full_core__splitx.sv $O/splitf_vb.sv $O/xf_old__fs.sv $O/xf_new__fs.sv $EB/bench/oc/s__fs.sv $RX/ot_hbm_su_pg_lane_full_x_core.sv $RX/ot_hbm_su_static_lane_x.sv $RX/ot_hbm_su_static_lane_pinreg_x.sv src/core_vd.sv $S/gen_xd/ot_hbm_su_static_lane_xb.sv $S/gen_xd/ot_hbm_su_static_lane_pinreg_xb.sv $RX/ot_hbm_su_pg_sfu_s_core.sv $LEAF $H/sram_bench_model.sv > $O/build_$T.log 2>&1 || { echo BUILD FAIL $T; tail -20 $O/build_$T.log | cut -c1-300; continue; }
  $O/obj_$T/sim > $O/sim_$T.log 2>&1; echo "$O MUT $M SIDE_D $D: $(grep XEQ $O/sim_$T.log)"; grep MISMATCH $O/sim_$T.log | head -3 | cut -c1-140
  rm -rf $O/obj_$T
done
