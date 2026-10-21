#!/bin/bash
# TOK-FUNC2-ENG_TAP (10-21): closure-loop bench of the Engram tap (dsdv_eng_tap / dsdv_eng_tap_w = dsdv_eng_tap_c) in
# its real context: tb_dsdv_eng_rr (16 taps + 16 real dsfd_ctrl_rg3 + lookup + XQ, python bit-exact vs hdc_golden_v41),
# built from the job's source snapshot (cwd), Verilator 5.050 (the daemon's).
#   bench_tap_snapshot.sh <work dir> <base|tap1|tap2> [plusargs...]
# Prints ENG_TAP_BENCH PASS <variant> (TB_ENG_RR PASS + ENG_RR_PY PASS, with the row-beat count) or ENG_TAP_BENCH FAIL.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
command -v $VL >/dev/null 2>&1 || VL=verilator
F=($(python3 - tools/s81_dv/eng_rr/run_eng_rr.sh <<'PY'
import re, sys
print(' '.join(re.search(r'F=\((.*?)\)\n', open(sys.argv[1]).read(), re.S).group(1).split()))
PY
))
case $V in base) G=();; tap1) G=(-GTAP_MUT=1);; tap2) G=(-GTAP_MUT=2);; *) echo "ENG_TAP_BENCH FAIL bad variant $V"; exit 2;; esac
python3 tools/s81_dv/eng_rr/prep_rom.py $W/rom > $W/prep.log 2>&1 || { echo "ENG_TAP_BENCH FAIL prep_rom"; exit 1; }
$VL --version
$VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 +define+OT_ENGRAM_CRCMAT --top-module tb_dsdv_eng_rr "${G[@]}" "${F[@]}" \
    --Mdir $W/obj -o sim > $W/build.log 2>&1 || { tail -20 $W/build.log; echo "ENG_TAP_BENCH FAIL build"; exit 1; }
$W/obj/sim +OT_ROM_DIR=$W/rom "$@" > $W/run.log 2>&1
python3 tools/s81_dv/eng_rr/check_eng_rr.py $W/run.log $PWD >> $W/run.log 2>&1
grep -h 'TB_ENG_RR_STATS\|TB_ENG_RR PASS\|TB_ENG_RR FAIL\|ENG_RR_PY' $W/run.log | tail -6
if grep -q 'TB_ENG_RR PASS' $W/run.log && grep -q 'ENG_RR_PY PASS' $W/run.log; then echo "ENG_TAP_BENCH PASS $V"; exit 0; fi
echo "ENG_TAP_BENCH FAIL $V"; exit 1
