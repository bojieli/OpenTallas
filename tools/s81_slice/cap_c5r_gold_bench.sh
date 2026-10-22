#!/bin/bash
# cap_c5r_gold_bench.sh (S81-CAPRST 10-21 successor capc5r: regional reset ports) <outdir> <vecdir> [MUT] [raw] (cwd = repo root): S81-CAPC4 10-20 -- the LANDED capture cluster
# ot_s81sl_capc5c (VARIANT C S81-CAPC5, lp.py from ot_s81sl_capc5cf, children at the hard-view parameters ED 24 / LD 16) on the GOLDEN cap_model
# vectors with the s_16_24 calendar launch advance: every golden row written at W + 8 (S and N leaves) exactly once, every lane arrival at its
# advanced edge, fault 0 (tb rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_capc5r_gold.sv).  MUT 0 must PASS; MUT 1 / 2 / 4 (lp.py
# landing bypass / landing read K+1 / u_rt reset run +1) are RTL mutants that must FAIL (raw: print CAP_C5R_MUTANT_DETECTED, exit 1).
set -u; O=$1; VD=$2; M=${3:-0}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version
srcs="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv
 rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/hdc/ot_hdc_cg.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv
 rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv
 rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r.sv
 rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_capc5r_gold.sv"
if [ ! -x $O/obj/Vtb_s81sl_capc5r_gold ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M \
    --top-module tb_s81sl_capc5r_gold -Mdir $O/obj $srcs --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build.log 2>&1 || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
[ -f $VD/T ] || python3 tools/s81_slice/cap_model.py gen --case ${GEN_CASE:-real} --seed ${GEN_SEED:-1} --out $VD > $O/gen.log 2>&1 \
  || { echo "BENCH_SETUP_FAILED gen"; tail -3 $O/gen.log; exit 4; }
T=$(cat $VD/T); NW=$(cat $VD/NW)
/usr/bin/time -v -o $O/time_run.log $O/obj/Vtb_s81sl_capc5r_gold +DIR=$VD +T=$T +NW=$NW > $O/run.log 2>&1
grep -E "^SLCAP_GOLD|SLCAP_LATENCY|ARR_MISMATCH|WRITE_MISMATCH|MISSING|LAND_FAULT|%Fatal" $O/run.log | head -14
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && { echo "PASS cap_c5r_gold MUT=0 $(basename $VD)"; exit 0; }; echo "FAIL cap_c5r_gold"; exit 1; fi
if [ "${4:-}" = raw ]; then grep -q '^FAIL' $O/run.log && { echo "CAP_C5R_MUTANT_DETECTED MUT=$M $(basename $VD)"; exit 1; }; echo "CAP_C5R_MUTANT_BLIND MUT=$M"; exit 0; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; }
echo "NEGATIVE_CONTROL_PASSED MUT=$M (bench blind)"; exit 1
