#!/bin/bash
# rstop_sid_bench.sh <outdir> [MUT none|tiercol]  (cwd = repo root): S81-LBGAP G2 slice-id convention bench of ot_s81sl_rstop
# (tb_s81sl_rstop_sid: 16 real ring stops, sid = 2 * col + tier; line default hops W/E, own-beat zero-hop skip, NX snake
# ends map_e / map_w, V / line NX delivery).  MUT none must PASS; tiercol (the old {tier, col} decode) must FAIL.
# Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-none}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ $M = tiercol ] && D="+define+OT_S81SL_RSTOP_MUT_TIERCOL"
srcs="rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_sid.sv"
$V --version > $O/version_$M.log
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D --top-module tb_s81sl_rstop_sid -Mdir $O/obj_$M $srcs \
  --build-jobs ${J:-4} > $O/build_$M.log 2>&1 || { echo "BUILD_FAILED"; grep -m8 "%Error" $O/build_$M.log; exit 3; }
$O/obj_$M/Vtb_s81sl_rstop_sid > $O/run_$M.log 2>&1
grep -E "^MISMATCH|^PASS|^FAIL" $O/run_$M.log | head -12
if [ $M = none ]; then grep -q '^PASS rstop_sid' $O/run_$M.log && { echo "BENCH_PASS rstop_sid"; exit 0; }; echo "BENCH_FAIL rstop_sid"; exit 1; fi
grep -q '^FAIL rstop_sid' $O/run_$M.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M (bench blind)"; exit 1
