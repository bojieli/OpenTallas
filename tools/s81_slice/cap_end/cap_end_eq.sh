#!/bin/bash
# S81/PORTFIX-DEAD D-CAPEND: cap_end_eq.sh OUTDIR (repo root).  ot_s81sl_cap_w3 / _e6 vs ot_s81sl_cap #(24, 16) and the landed
# ot_s81sl_capc5r_w3 / _e6 vs ot_s81sl_capc5r, with the
# as-built lane ties, real-shape (seeds 1, 2) and random (seeds 1..3) cap_model.py streams.  Exit 0 = all PASS.
set -u; O=$1; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_dv/slice
srcs="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv
 rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/hdc/ot_hdc_cg.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv
 rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv
 $S/ot_s81sl_cap_tr.sv $S/ot_s81sl_cap_rt.sv $S/ot_s81sl_cap_ld.sv $S/ot_s81sl_cap_ed.sv $S/ot_s81sl_cap.sv
 $S/cap_end/ot_s81_retn_fwd.sv $S/cap_end/ot_s81sl_cap_trn.sv $S/cap_end/ot_s81sl_cap_rt_w.sv $S/cap_end/ot_s81sl_cap_end.sv
 rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv \
 $S/lp/ot_s81sl_capc5r.sv $S/lp/ot_s81sl_capc5r_w3.sv $S/lp/ot_s81sl_capc5r_e6.sv tools/s81_slice/cap_end/tb_cap_end_eq.sv tools/s81_slice/cap_end/tb_capc5r_end_eq.sv
 $S/ot_s81sl_cap_p1.sv $S/ot_s81sl_capc2.sv $S/cap_end/ot_s81sl_capc2_w3.sv tools/s81_slice/cap_end/tb_capc2_end_eq.sv"
rc=0
for TB in tb_cap_end_eq tb_capc5r_end_eq tb_capc2_end_eq; do for NL in 3 6; do
  [ $TB = tb_capc2_end_eq ] && [ $NL = 6 ] && continue
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GNL=$NL --top-module $TB -Mdir $O/obj_${TB}_$NL $srcs \
    --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_${TB}_$NL.log 2>&1 \
    || { echo "BUILD_FAILED NL=$NL"; grep -m8 "%Error" $O/build_${TB}_$NL.log; exit 3; }
  for v in real:1 real:2 random:1 random:2 random:3; do
    c=${v%:*}; s=${v#*:}; VD=$O/vec_${c}_$s
    [ -f $VD/T ] || python3 tools/s81_slice/cap_model.py gen --case $c --seed $s --out $VD > $O/gen_${c}_$s.log 2>&1 || { echo "GEN_FAILED $v"; exit 4; }
    $O/obj_${TB}_$NL/V$TB +DIR=$VD +T=$(cat $VD/T) > $O/run_${TB}_NL${NL}_${c}_$s.log 2>&1
    l=$(grep -h "END_EQ" $O/run_${TB}_NL${NL}_${c}_$s.log); echo "$c:$s $l"; echo "$l" | grep -q PASS || rc=1
  done
done; done
exit $rc
