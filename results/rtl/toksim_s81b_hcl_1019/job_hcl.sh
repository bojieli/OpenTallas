#!/usr/bin/env bash
# TOKSIM-S81B/HCL (10-19): HC load/store/coefficient cycles on the RELEASE source 19bf4121e (claude/s81-bind-mu4-1019).
#  A. vp beat leaf (ot_s81sl_vp + vn + vq): tb_toksim_hcl_beat (= tb_s81sl_beat + timers + HLS/GS plusargs), L0 and L2 real
#     1M layer chains (leaf_gold.py, su_cases_v2_ildr.pkl): HLOAD / GAIN / HSTORE / RDOUT cmd -> last write, and a sweep of the
#     HLOAD->GAIN (HLS) and GAIN->NORM (GS) issue spacing; every run keeps all golden checks of the original bench.
#  B. G-unit HC coefficient chain: rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh (MUT 0 + mutants) -> hc_lat.
# Fleet dir: /srv/opentallas-scratch/claude/toksim-s81b-hcl (src_hcl.tar = git archive 19bf4121e; bench + this script).
set -u
S=/srv/opentallas-scratch/claude/toksim-s81b-hcl
W=$S/src; rm -rf $W; mkdir -p $W && tar xf $S/src_hcl.tar -C $W || exit 1
O=$S/out; rm -rf $O; mkdir -p $O; cd $W || exit 1
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
echo "HOST $(hostname) start $(date) src 19bf4121e"; verilator --version
CASES=tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl
MACV="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
srcs="$(sort -u physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') rtl/hdc/v41x/ot_dsrom_su_add6.sv $MACV rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
# B in the background
( bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh $O/gunit 8 > $O/gunit.txt 2>&1; echo "EXIT $?" >> $O/gunit.txt ) &
# A: one build (plusargs), golden for L0 / L2
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GBEAT=37 -GVQ_XMEM=0 --top-module tb_toksim_hcl_beat -Mdir $O/obj $srcs \
  $S/tb_toksim_hcl_beat.sv --build-jobs 8 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -20 $O/build.log; }
for L in L0 L2; do
  mkdir -p $O/run_$L; python3 tools/s81_slice/leaf_gold.py $CASES 37 $O/run_$L $L > $O/gold_$L.log 2>&1 || { echo "GOLD FAIL $L"; tail -5 $O/gold_$L.log; }
  for HLS in 40 32 24 20 19 18 17 16 15; do
    ( cd $O/run_$L && ../obj/Vtb_toksim_hcl_beat +HLS=$HLS +GS=20 > ../r_${L}_hls${HLS}_gs20.log 2>&1 )
    echo "$L HLS=$HLS GS=20: $(grep -E '^HCLBEAT' $O/r_${L}_hls${HLS}_gs20.log) $(grep -cE 'MISMATCH' $O/r_${L}_hls${HLS}_gs20.log) mism $(grep -E '^(PASS|FAIL)' $O/r_${L}_hls${HLS}_gs20.log)"
  done
  for GS in 16 12 10 9 8 7 6; do
    ( cd $O/run_$L && ../obj/Vtb_toksim_hcl_beat +HLS=40 +GS=$GS > ../r_${L}_hls40_gs${GS}.log 2>&1 )
    echo "$L HLS=40 GS=$GS: $(grep -E '^HCLBEAT' $O/r_${L}_hls40_gs${GS}.log) $(grep -cE 'MISMATCH' $O/r_${L}_hls40_gs${GS}.log) mism $(grep -E '^(PASS|FAIL)' $O/r_${L}_hls40_gs${GS}.log)"
  done
  grep -E '^SLBEAT' $O/r_${L}_hls40_gs20.log
done
wait
echo "== gunit"; cat $O/gunit.txt
echo "HOST $(hostname) done $(date)"
