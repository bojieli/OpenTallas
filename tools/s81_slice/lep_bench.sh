#!/bin/bash
# lep_bench.sh <outdir> [MUT none|swap|nopair|noovf|ksoff|hdrop|nhacc] [SEED] [BENCH lep|lep_host|lep_nhr|lep_nh]  (cwd = repo root):
# RTL-BUILD-S81 end-slice link-port benches.
#   lep       tb_s81sl_lep: two dies, ot_s81sl_lep + 2 x dsfd_coll_lane_{w,e} + 2 x ot_pdie_ucie each, ring beats both ways
#   lep_host  tb_s81sl_lep_host: lep die vs a host-side endpoint model: ring + HOST / KS in, ring + THOST / TKD out, f_lf
#   lep_nhr   tb_s81sl_lep +define+TB_LEP_NH: the ring bench with both dies = ot_s81sl_lep_nh (HOST_EN 0, S81-LEPV)
#   lep_nh    tb_s81sl_lep_nh: ot_s81sl_lep_nh vs a frame codec: ring both ways, no host-plane frame out, HOST / KS in -> fault
# MUT none must PASS; the mutants must FAIL ("^FAIL <bench>:").  Exit 0 = PASS line only (raw verdict).
set -u; O=$1; M=${2:-none}; S=${3:-1}; T=${4:-lep}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ $M != none ] && D="+define+OT_S81SL_LEP_MUT_$(echo $M | tr a-z A-Z)"
TB=$T; [ $T = lep_nhr ] && { TB=lep; D="$D +define+TB_LEP_NH"; }
srcs="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_$TB.sv"
R=${T}_${M}_$S
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN $D -GSEED=$S --top-module tb_s81sl_$TB \
  -Mdir $O/obj_$R $srcs --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_$R.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build_$R.log; exit 3; }
$O/obj_$R/Vtb_s81sl_$TB > $O/run_$R.log 2>&1
grep -E "^LEP|^MISMATCH|^PASS|^FAIL" $O/run_$R.log | head -12
grep -q "^PASS $TB:" $O/run_$R.log && { echo "BENCH_PASS $T MUT=$M seed $S"; exit 0; }; echo "BENCH_FAIL $T MUT=$M seed $S"; exit 1
