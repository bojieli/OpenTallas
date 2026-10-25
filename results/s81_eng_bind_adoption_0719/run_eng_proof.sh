#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
read -ra files < files.txt
for mut in 0 1; do
 "$VL" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -CFLAGS -O1 +define+ADOPT_MUT=$mut +define+OT_S81ENG_RR_N32 +define+OT_S81ENG_RR_MUL_N32 +define+OT_ENGRAM_CRCMAT --top-module tb_dsdv_eng_rr "${files[@]}" --Mdir obj_$mut -o sim > build_$mut.log 2>&1 || { tail -20 build_$mut.log; exit 2; }
 if obj_$mut/sim +OT_ROM_DIR=$PWD/rom > run_$mut.log 2>&1; then
  if [ "$mut" != 0 ]; then echo ADOPT_MUTANT_ESCAPED; exit 1; fi
  grep -q ADOPT_LOCKSTEP_PASS run_$mut.log || exit 1
 else
  if [ "$mut" = 0 ]; then tail -15 run_$mut.log; exit 1; fi
  grep -q ADOPT_LOCKSTEP run_$mut.log || exit 1
  echo ADOPT_MUTANT_CAUGHT
 fi
done
grep -E 'ADOPT_LOCKSTEP_PASS|TB_ENG_RR_STATS|TB_ENG_RR PASS' run_0.log
