#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
RUN=${1:?fresh output}
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
python3 "$ROOT/results/token_pass/s81_entry39_2148/sources.py" "$ROOT" "$RUN"
mapfile -t DEFINES < "$RUN/defines.txt"
D=();for d in "${DEFINES[@]}";do D+=("+define+$d");done
verilator --binary --timing -j 2 --build-jobs 1 -Wno-fatal --top-module tb_entry39 "${D[@]}" "$RUN/selected.sv" "$ROOT/rtl/dsrom_sys/s81_dv/eng/dsdv_eng_tap_entry39.sv" "$ROOT/results/token_pass/s81_entry39_2148/tb.sv" -Mdir "$RUN/obj" > "$RUN/build.log" 2>&1
"$RUN/obj/Vtb_entry39" > "$RUN/base.log" 2>&1
set +e
"$RUN/obj/Vtb_entry39" +MUT_PACK > "$RUN/mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ];then echo MUTANT_ESCAPED;exit 1;fi
grep -q ENTRY39_PASS "$RUN/base.log"
grep -q ENTRY39.mismatch "$RUN/mutant.log"
echo ENTRY39_GATE_PASS
