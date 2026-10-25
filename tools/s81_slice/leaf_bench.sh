#!/bin/bash
# leaf_bench.sh <outdir> [MUT 0..6] [L0|L2] [BEAT]  (cwd = repo root): S81-TILES5 slice bench -- ONE ot_s81sl_leaf (the
# beat leaf exactly as ot_s81sl_slice wires it: vp + vn + vq AQ_XMEM 2 + vs + vsw + hub RA lane pair) on one layer's
# 1M-token SU cases (tools/s81_slice/vs_gold.py).  MUT 0 must PASS; MUT 1..6 (vs negative controls) must FAIL.
# S81SL_VQ_XMEM=0 builds vq with the flop wait line instead.  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-0}; L=${3:-L0}; B=${4:-37}; mkdir -p $O/run
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
CASES=${S81_SU_CASES:-tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl}
python3 tools/s81_slice/vs_gold.py $CASES $O/run $L > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -5 $O/gold.log; exit 4; }
MACV="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
srcs="$(cat physical/hbm_norm_split_20261008/sources.f rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f | sort -u | tr '\n' ' ') $MACV
 rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_leaf.sv"   # ve: the leaf's Engram sub-leaf (RTL-BUILD-S81)
/usr/bin/time -v -o $O/time.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M -GBEAT=$B -GXMEM=${S81SL_VQ_XMEM:-2} \
  --top-module tb_s81sl_leaf -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY|PINNOCONNECT" $O/build.log | grep -i "s81sl_leaf\|s81sl_slice" | head -5
(cd $O/run && ../obj/Vtb_s81sl_leaf > ../run.log 2>&1)
grep -E "^VSOP|^SLVS|MISMATCH|TIMEOUT" $O/run.log | head -40
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && { echo "PASS leaf MUT=0 $L XMEM=${S81SL_VQ_XMEM:-2}"; exit 0; }; echo "FAIL leaf"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M $L"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M $L (bench blind)"; exit 1
