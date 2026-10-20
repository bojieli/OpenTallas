#!/bin/bash
# cap_p1_gold_bench.sh <outdir> <vecdir> [DE] [DL] [raw] (cwd = repo root): LEAD2-S81/CAPC2 10-19 -- ot_s81sl_cap_p1 #(PINPIPE 1,
# EDLY DE, WL3DLY DL) on the GOLDEN cap_model vectors with the s_16_24 calendar launch advance (E lanes 24 edges, W lane 3 16 edges
# earlier): every golden row written at W + 2 exactly once, every lane arrival at its advanced edge, fault 0.
# DE 24 / DL 16 must PASS; DE != 24 or DL != 16 are RTL mutants that must FAIL (raw: print CAP_GOLD_MUTANT_DETECTED, exit 1).
set -u; O=$1; VD=$2; DE=${3:-24}; DL=${4:-16}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > $O/verilator.version
srcs="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv
 rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/hdc/ot_hdc_cg.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv
 rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_p1.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_cap_p1_gold.sv"
if [ ! -x $O/obj/Vtb_s81sl_cap_p1_gold ]; then
  /usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GDE=$DE -GDL=$DL \
    --top-module tb_s81sl_cap_p1_gold -Mdir $O/obj $srcs --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build.log 2>&1 || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
fi
[ -f $VD/T ] || python3 tools/s81_slice/cap_model.py gen --case ${GEN_CASE:-real} --seed ${GEN_SEED:-1} --out $VD > $O/gen.log 2>&1 \
  || { echo "BENCH_SETUP_FAILED gen"; tail -3 $O/gen.log; exit 4; }
T=$(cat $VD/T); NW=$(cat $VD/NW)
/usr/bin/time -v -o $O/time_run.log $O/obj/Vtb_s81sl_cap_p1_gold +DIR=$VD +T=$T +NW=$NW > $O/run.log 2>&1
grep -E "^SLCAP_GOLD|ARR_MISMATCH|WRITE_MISMATCH|MISSING|%Fatal" $O/run.log | head -14
if [ "$DE" = 24 ] && [ "$DL" = 16 ]; then grep -q '^PASS' $O/run.log && { echo "PASS cap_p1_gold DE=24 DL=16 $(basename $VD)"; exit 0; }; echo "FAIL cap_p1_gold"; exit 1; fi
if [ "${5:-}" = raw ]; then grep -q '^FAIL' $O/run.log && { echo "CAP_GOLD_MUTANT_DETECTED DE=$DE DL=$DL $(basename $VD)"; exit 1; }; echo "CAP_GOLD_MUTANT_BLIND DE=$DE DL=$DL"; exit 0; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED DE=$DE DL=$DL"; exit 0; }
echo "NEGATIVE_CONTROL_PASSED DE=$DE DL=$DL (bench blind)"; exit 1
