#!/bin/bash
# slice_eng_bench.sh <outdir> [VS_MUT 0|7|8] [SEED]  (cwd = repo root): RTL-BUILD-S81 Engram mix of one V4.1 layer on ONE
# real ot_s81sl_slice (5 beat leaves with vs op 14 + ve, xr ENG, xfin ENG, eg; tb_s81sl_slice_eng), the other 15 slices'
# exchange flits golden-injected (tools/s81_slice/eng_slice_gold.py = Model.engram_layer statements, chunk8).
# VS_MUT 0 must PASS; 7 / 8 must FAIL.  Exit 0 = the expected verdict; RAW=1: exit 0 only on PASS.
set -u; O=$1; M=${2:-0}; S=${3:-3}; mkdir -p $O/fx
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_slice/eng_slice_gold.py $O/fx --seed $S > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -5 $O/gold.log; exit 4; }
MAC="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v"
CAL="rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv"
XS="rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv $CAL rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv"
CAP="rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/hdc/ot_hdc_cg.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_p1.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_capc2.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/lib/ot_rst_relay.sv"
EG=$(ls rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg*.sv 2>/dev/null | grep -v test | tr '\n' ' ')
SL=${SLICE_SRCS:-rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv}
srcs="$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f | sort -u | tr '\n' ' ') $MAC
 rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv $EG
 rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv $XS $CAP $SL ${SLICE_ENG_TB:-rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_slice_eng.sv}"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 -GVS_MUT=$M --top-module tb_s81sl_slice_eng -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; grep -m8 "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/build.log | grep -i "s81sl_\|s81dv_" | head -8
$O/obj/Vtb_s81sl_slice_eng +dir=$O/fx > $O/run.log 2>&1
grep -E "^SLICEENG|MISMATCH|TIMEOUT|^PASS|^FAIL" $O/run.log | head -20
if [ "$M" = 0 ] || [ -n "${RAW:-}" ]; then grep -q '^PASS' $O/run.log && { echo "PASS slice_eng VS_MUT=$M seed=$S"; exit 0; }; echo "FAIL slice_eng VS_MUT=$M"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED VS_MUT=$M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED VS_MUT=$M (bench blind)"; exit 1
