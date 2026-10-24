#!/bin/bash
# CORE-S81-ENG (10-23): lockstep bench of the two-core split dsdv_eng_rr_split (cores dsdv_eng_rr_lk + dsdv_eng_rr_xq)
# against the monolithic dsdv_eng_rr_c in tb_dsdv_eng_rr (OT_S81ENG_RR_SPLIT_LOCKSTEP): the monolith drives the bench
# system (python bit-exact vs hdc_golden_v41 as in bench_rr_snapshot.sh), the split runs on the same inputs and every
# output bit + the crossing is compared on every edge.   bench_rr_split.sh <work dir> <base|sm1|sm2> [plusargs...]
# sm1 / sm2 = SPLIT_MUT negative controls (crossing bit flip / one extra crossing stage): must FAIL.
# Prints ENG_RR_SPLIT PASS <variant> or ENG_RR_SPLIT FAIL <variant>.  Run from the repo root.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
command -v $VL >/dev/null 2>&1 || VL=verilator
F=($(python3 - tools/s81_dv/eng_rr/run_eng_rr.sh <<'PY'
import re, sys
print(' '.join(re.search(r'F=\((.*?)\)\n', open(sys.argv[1]).read(), re.S).group(1).split()))
PY
))
F=("${F[@]:0:${#F[@]}-1}" rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv "${F[@]: -1}")
case $V in base) G=();; sm1) G=(-GSPLIT_MUT=1);; sm2) G=(-GSPLIT_MUT=2);; *) echo "ENG_RR_SPLIT FAIL bad variant $V"; exit 2;; esac
python3 tools/s81_dv/eng_rr/prep_rom.py $W/rom > $W/prep.log 2>&1 || { echo "ENG_RR_SPLIT FAIL prep_rom"; exit 1; }
$VL --version
$VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 +define+OT_S81ENG_RR_N32 +define+OT_S81ENG_RR_MUL_N32 +define+OT_ENGRAM_CRCMAT \
    +define+OT_S81ENG_RR_SPLIT_LOCKSTEP --top-module tb_dsdv_eng_rr "${G[@]}" "${F[@]}" --Mdir $W/obj -o sim > $W/build.log 2>&1 \
    || { tail -20 $W/build.log; echo "ENG_RR_SPLIT FAIL build"; exit 1; }
$W/obj/sim +OT_ROM_DIR=$W/rom "$@" > $W/run.log 2>&1
python3 tools/s81_dv/eng_rr/check_eng_rr.py $W/run.log $PWD >> $W/run.log 2>&1
grep -h 'TB_ENG_RR_STATS\|TB_ENG_RR_LOCKSTEP\|TB_ENG_RR PASS\|TB_ENG_RR FAIL\|ENG_RR_PY' $W/run.log | tail -8
if grep -q 'TB_ENG_RR PASS' $W/run.log && grep -q 'ENG_RR_PY PASS' $W/run.log && \
   grep -q 'TB_ENG_RR_LOCKSTEP .* mismatches 0$' $W/run.log; then echo "ENG_RR_SPLIT PASS $V"; exit 0; fi
echo "ENG_RR_SPLIT FAIL $V"; exit 1
