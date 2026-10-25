#!/bin/bash
# S81-ELEM2-ENGRR (10-21): closure-loop bench of the whole-RR successor dsdv_eng_rr (OT_S81ENG_RR_N32 + OT_S81ENG_RR_MUL_N32,
# the kit's synthesis profile) in tb_dsdv_eng_rr (python bit-exact vs hdc_golden_v41), built from the job's source snapshot
# (cwd) with Verilator 5.050 (the daemon's).   bench_rr_snapshot.sh <work dir> <base|xq1|onesc> [plusargs...]
# Prints ENG_RR_BENCH PASS <variant> or ENG_RR_BENCH FAIL <variant>.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
command -v $VL >/dev/null 2>&1 || VL=verilator
F=($(python3 - tools/s81_dv/eng_rr/run_eng_rr.sh <<'PY'
import re, sys
print(' '.join(re.search(r'F=\((.*?)\)\n', open(sys.argv[1]).read(), re.S).group(1).split()))
PY
))
# S81/PORTFIX-CFG 10-25: cfg1 / cfg2 = CFG_MUT 1 (rank bits swapped) / 2 (cfg decode on kind only) must FAIL; sref = the
# old-strap dsdv_eng_rr_c in bit-exact lockstep with the cfg-configured die master (OT_ENG_CFG_STRAPREF) must PASS.
case $V in base) G=();; xq1) G=(-GXQ_MUT=1);; onesc) G=(+define+OT_ENGRAM_MUT_ONESCALE);;
  cfg1) G=(-GCFG_MUT=1);; cfg2) G=(-GCFG_MUT=2);; sref) G=(+define+OT_ENG_CFG_STRAPREF);;
  *) echo "ENG_RR_BENCH FAIL bad variant $V"; exit 2;; esac
python3 tools/s81_dv/eng_rr/prep_rom.py $W/rom > $W/prep.log 2>&1 || { echo "ENG_RR_BENCH FAIL prep_rom"; exit 1; }
$VL --version
$VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 +define+OT_S81ENG_RR_N32 +define+OT_S81ENG_RR_MUL_N32 +define+OT_ENGRAM_CRCMAT \
    --top-module tb_dsdv_eng_rr "${G[@]}" "${F[@]}" --Mdir $W/obj -o sim > $W/build.log 2>&1 || { tail -20 $W/build.log; echo "ENG_RR_BENCH FAIL build"; exit 1; }
$W/obj/sim +OT_ROM_DIR=$W/rom "$@" > $W/run.log 2>&1
python3 tools/s81_dv/eng_rr/check_eng_rr.py $W/run.log $PWD >> $W/run.log 2>&1
grep -h 'TB_ENG_RR_STATS\|TB_ENG_RR_STRAPREF\|TB_ENG_RR PASS\|TB_ENG_RR FAIL\|ENG_RR_PY' $W/run.log | tail -6
if grep -q 'TB_ENG_RR PASS' $W/run.log && grep -q 'ENG_RR_PY PASS' $W/run.log; then echo "ENG_RR_BENCH PASS $V"; exit 0; fi
echo "ENG_RR_BENCH FAIL $V"; exit 1
