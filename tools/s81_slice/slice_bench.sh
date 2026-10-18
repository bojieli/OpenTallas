#!/bin/bash
# slice_bench.sh <outdir> [MUT 0..6] [L0|L2] [BEAT]  (cwd = repo root): S81-TILES6 WHOLE-slice mode of leaf_bench.sh -- the
# same 1M-token SU cases (tools/s81_slice/vs_gold.py) through the whole ot_s81sl_slice (5 x ot_s81sl_leaf + xg (rstop + xs)
# + xr1 + cap + xfin + relays), stimulus and checks at the slice pins (tb_s81sl_slice).  MUT 0 must PASS; MUT 1..6 (vs
# negative controls through the slice's VS_MUT) must FAIL.  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-0}; L=${3:-L0}; B=${4:-37}; mkdir -p $O/run
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
CASES=${S81_SU_CASES:-tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl}
# the golden needs numpy >= 2 (pickled cases): a run dir already holding prog.mem (made on such a host) is reused
[ -s $O/run/prog.mem ] || python3 tools/s81_slice/vs_gold.py $CASES $O/run $L > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -5 $O/gold.log; exit 4; }
MACV="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
srcs="$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f rtl/dsrom_sys/s81_dv/slice/test/slice_extra.f | awk '!s[$0]++' | tr '\n' ' ') $MACV
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_slice.sv"
/usr/bin/time -v -o $O/time.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
  -GMUT=$M -GBEAT=$B -GXMEM=${S81SL_VQ_XMEM:-2} --top-module tb_s81sl_slice -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT|PINNOTFOUND" $O/build.log | grep -v "tb_s81sl_slice.sv" | head -5
(cd $O/run && ../obj/Vtb_s81sl_slice > ../run.log 2>&1)
grep -E "^VSOP|^SLSL|MISMATCH|TIMEOUT" $O/run.log | head -40
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && { echo "PASS slice MUT=0 $L XMEM=${S81SL_VQ_XMEM:-2}"; exit 0; }; echo "FAIL slice"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M $L"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M $L (bench blind)"; exit 1
