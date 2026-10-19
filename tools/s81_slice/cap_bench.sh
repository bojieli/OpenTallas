#!/bin/bash
# cap_bench.sh <outdir> <vecdir> [MUT] [raw] (cwd = repo root): S81-SLICE capture-root bench (ot_s81sl_cap behind 8 real die
# return chains dsfd_node_NNfu -> dsfd_rstg -> dsfd_cfifo_crs).  Vectors: tools/s81_slice/cap_model.py gen.
# MUT 0 must PASS; MUT 1..4 (wrong sibling association, ri bit order, leaf off by one, dropped partial) must FAIL.
# Exit 0 = the expected verdict.  raw (closure-loop expect=fail benches): a mutant that is detected prints
# CAP_MUTANT_DETECTED MUT=<n> and exits 1; a blind mutant exits 0.
set -u; O=$1; VD=$2; M=${3:-0}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
srcs="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv
 rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/hdc/ot_hdc_cg.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv
 rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_cap.sv"
if [ ! -x $O/obj/Vtb_s81sl_cap ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M \
    --top-module tb_s81sl_cap -Mdir $O/obj $srcs --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build.log 2>&1 || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
# a missing vector dir is generated: the real-shape stream (3 phases x 320 rows, seed 1) of the committed evidence
[ -f $VD/T ] || python3 tools/s81_slice/cap_model.py gen --case ${GEN_CASE:-real} --seed ${GEN_SEED:-1} --out $VD > $O/gen.log 2>&1 \
  || { echo "BENCH_SETUP_FAILED gen"; tail -3 $O/gen.log; exit 4; }
T=$(cat $VD/T); NW=$(cat $VD/NW)
/usr/bin/time -v -o $O/time_run.log $O/obj/Vtb_s81sl_cap +DIR=$VD +T=$T +NW=$NW > $O/run.log 2>&1
grep -E "^SLCAP|MISMATCH|MISSING" $O/run.log | head -14
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && { echo "PASS cap MUT=0 $(basename $VD)"; exit 0; }; echo "FAIL cap"; exit 1; fi
if [ "${4:-}" = raw ]; then grep -q '^FAIL' $O/run.log && { echo "CAP_MUTANT_DETECTED MUT=$M $(basename $VD)"; exit 1; }; echo "CAP_MUTANT_BLIND MUT=$M"; exit 0; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M $(basename $VD)"; exit 0; }
echo "NEGATIVE_CONTROL_PASSED MUT=$M (bench blind)"; exit 1
