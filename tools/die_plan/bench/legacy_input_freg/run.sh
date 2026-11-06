#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p out_final
rtl_dir=src
if [[ ! -f "$rtl_dir/ot_dp_clk_landing.sv" ]]; then
  rtl_dir="$(cd ../../../.. && pwd)/rtl/common"
fi
for mode in baseline bypass bit fall; do
  defs=()
  case "$mode" in
    bypass) defs+=(-DOT_LEGACY_FREG_MUTANT_BYPASS);;
    bit) defs+=(-DOT_LEGACY_FREG_MUTANT_BIT);;
    fall) defs+=(-DOT_LEGACY_FREG_MUTANT_FALL);;
  esac
  verilator --binary --timing --top-module tb_legacy_input_freg -Wno-fatal -j 2 \
    "${defs[@]}" --Mdir "out_final/obj_$mode" tb_legacy_input_freg.sv ot_dp_clk_landing_gold.sv "$rtl_dir/ot_dp_clk_landing.sv" "$rtl_dir/ot_meso_fifo.sv" \
    >"out_final/build_$mode.log" 2>&1
  if [[ "$mode" == baseline ]]; then
    for phase in 0 1 50 200 400 416 417 600 800 832; do
      "out_final/obj_$mode/Vtb_legacy_input_freg" "+PHASE=$phase" >>out_final/baseline.log 2>&1
    done
  else
    set +e
    "out_final/obj_$mode/Vtb_legacy_input_freg" +PHASE=50 >"out_final/mutant_$mode.log" 2>&1
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then echo "MUTANT_NOT_CAUGHT $mode";exit 1;fi
    if [[ "$mode" != fall ]]; then
      grep -Eq 'CASE_RESULT WNEG=1 checks=[0-9]+ errors=[1-9][0-9]*' "out_final/mutant_$mode.log"
    fi
    grep 'CASE_RESULT' "out_final/mutant_$mode.log" >>out_final/result.txt
    echo "MUTANT_CAUGHT $mode rc=$rc" >>out_final/result.txt
  fi
done
cat out_final/baseline.log >>out_final/result.txt
echo LEGACY_INPUT_FREG_ALL_PASS >>out_final/result.txt
