#!/bin/bash
# xfin_eng_bench.sh <outdir> [base|mutetag|muteassoc] [ORD 0|1] [GAP] [SEED] [raw]  (cwd = repo root): RTL-BUILD-S81
# xfin ENG mode -- tb_s81dv_xfin16e: 16 real ot_s81dv_xfin on the snake exchange ring, golden Engram csum totals
# (tools/s81_dv/xfin_eng_golden.py, hdc_golden_v41 chunk8).  base must print PASS; mutetag (slice 3 swaps vector tags
# 1 / 5) and muteassoc (tree nodes 4 / 5 re-associated) must FAIL.  Exit 0 = the expected verdict (raw: the bench
# verdict itself).
set -u; O=$1; M=${2:-base}; ORD=${3:-0}; GAP=${4:-0}; SEED=${5:-1}; RAW=${6:-}; mkdir -p $O/run
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_dv/xfin_eng_golden.py $O/run --seed $SEED > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -3 $O/gold.log; exit 4; }
DEF=""; [ "$M" = mutetag ] && DEF="+define+OT_S81DV_MUT_ETAG"; [ "$M" = muteassoc ] && DEF="+define+OT_S81DV_MUT_EASSOC"; [ "$M" = rtlcxfin ] && DEF="+define+OT_RTLC_MUT_XFIN"
srcs="$(cat physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/test/tb_s81dv_xfin16e.sv"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GORD=$ORD -GGAP=$GAP --top-module tb_s81dv_xfin16e -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY" $O/build.log | grep -v "tb_s81dv" | head -3
(cd $O/run && ../obj/Vtb_s81dv_xfin16e > ../run.log 2>&1)
grep -E "^DV|MISMATCH|MISSING|DUP" $O/run.log | head -9
if [ "$RAW" = raw ]; then grep -E "^(PASS|FAIL)" $O/run.log | head -1; grep -q "^PASS" $O/run.log; exit $?; fi
if [ "$M" = base ]; then grep -q '^PASS' $O/run.log && { echo "PASS dvxfin16e ORD=$ORD GAP=$GAP SEED=$SEED"; exit 0; }; echo "FAIL dvxfin16e"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
