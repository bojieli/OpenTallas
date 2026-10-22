#!/bin/bash
# S81-ELEM2-ENGRR (10-21): closure-loop bench of the lookup RA640 through the integrated dsdv_eng_rr harness (lookup kit CRCMAT,
# the kit's synthesis profile) in tb_dsdv_eng_rr (python bit-exact vs hdc_golden_v41), built from the job's source snapshot
# (cwd) with Verilator 5.050 (the daemon's).   bench_rr_snapshot.sh <work dir> <base|rpar|onesc> [plusargs...]
# Prints LOOKUP_BENCH PASS <variant> or LOOKUP_BENCH FAIL <variant>.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
command -v $VL >/dev/null 2>&1 || VL=verilator
F=($(python3 - tools/s81_dv/eng_rr/run_eng_rr.sh <<'PY'
import re, sys
print(' '.join(re.search(r'F=\((.*?)\)\n', open(sys.argv[1]).read(), re.S).group(1).split()))
PY
))
case $V in base) G=();; rpar) G=(+define+OT_ENGRAM_MUT_RA512_PAR);; onesc) G=(+define+OT_ENGRAM_MUT_ONESCALE);; *) echo "LOOKUP_BENCH FAIL bad variant $V"; exit 2;; esac
python3 tools/s81_dv/eng_rr/prep_rom.py $W/rom > $W/prep.log 2>&1 || { echo "LOOKUP_BENCH FAIL prep_rom"; exit 1; }
$VL --version
$VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 +define+OT_ENGRAM_CRCMAT \
    --top-module tb_dsdv_eng_rr "${G[@]}" "${F[@]}" --Mdir $W/obj -o sim > $W/build.log 2>&1 || { tail -20 $W/build.log; echo "LOOKUP_BENCH FAIL build"; exit 1; }
$W/obj/sim +OT_ROM_DIR=$W/rom "$@" > $W/run.log 2>&1
python3 tools/s81_dv/eng_rr/check_eng_rr.py $W/run.log $PWD >> $W/run.log 2>&1
grep -h 'TB_ENG_RR_STATS\|TB_ENG_RR PASS\|TB_ENG_RR FAIL\|ENG_RR_PY' $W/run.log | tail -6
if grep -q 'TB_ENG_RR PASS' $W/run.log && grep -q 'ENG_RR_PY PASS' $W/run.log; then echo "LOOKUP_BENCH PASS $V"; exit 0; fi
if grep -Eq "ENG_RR_PY windows [0-9]+ checked [0-9]+ errs [1-9][0-9]*" $W/run.log && grep -q "TB_ENG_RR FAIL" $W/run.log; then echo "LOOKUP_CAUSAL_FAIL $V"; exit 1; fi
echo "LOOKUP_BENCH INFRASTRUCTURE_OR_UNCLASSIFIED $V"; exit 2
