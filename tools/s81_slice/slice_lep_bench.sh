#!/bin/bash
# slice_lep_bench.sh <outdir> [MUT none|swap] [B lepe|lepe_nh]  (cwd = repo root): RTL-BUILD-S81 composition bench of the end-slice masters
# (tb_s81sl_slice_lep: ot_s81sl_slice_lepw + ot_s81sl_slice_lepe, full slice clusters, through 2 x 2 ot_pdie_ucie).
set -u; O=$1; M=${2:-none}; BV=${3:-lepe}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ $M = swap ] && D="+define+OT_S81SL_LEP_MUT_SWAP"; [ $BV = lepe_nh ] && D="$D +define+TB_SLEP_NH"; M0=$M; M=${M}_$BV
MAC="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v"
CEN="rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_p1.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_capc2.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/lib/ot_rst_relay.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv
 rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv
 rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv"
LEP="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_slice_lep.sv
 rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv
 $(ls rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg*.sv 2>/dev/null | tr '\n' ' ')"
srcs="$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f | sort -u | tr '\n' ' ') $MAC $CEN $LEP"
/usr/bin/time -v -o $O/time_$M.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+DSFD_PQ_STATIC_X2 $D \
  --top-module tb_s81sl_slice_lep -Mdir $O/sobj_$M $srcs --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/sbuild_$M.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m10 -E "%Error" $O/sbuild_$M.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/sbuild_$M.log | grep -v "tb_s81sl_slice_lep" | head -8
$O/sobj_$M/Vtb_s81sl_slice_lep > $O/srun_$M.log 2>&1
grep -E "^SLEP_STATS|^MISMATCH|^PASS|^FAIL" $O/srun_$M.log | head -10
if [ $M0 = none ]; then grep -q '^PASS slice_lep' $O/srun_$M.log && { echo "BENCH_PASS slice_lep"; exit 0; }; echo "BENCH_FAIL slice_lep"; exit 1; fi
grep -q '^FAIL slice_lep' $O/srun_$M.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M"; exit 1
