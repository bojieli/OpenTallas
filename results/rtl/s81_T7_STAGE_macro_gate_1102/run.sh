#!/bin/bash
# T7 staging macro gate (TOK-DS-4): build once, positive + 4 independent negative controls.
set -euo pipefail
ulimit -c 0
R=$(cd "$(dirname "$0")" && pwd)
cd "$R"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 make_mutants.py
sha256sum staging.sv sram.v mutants.sv tb.sv > inputs.sha256
/usr/bin/time -v "$V" --binary --timing -O1 -j 2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style \
  --top-module tb -Mdir "$R/obj" staging.sv sram.v mutants.sv tb.sv > build.log 2> build.err
set +e
/usr/bin/time -v ./obj/Vtb > positive.log 2> positive.time
rc=$?
set -e
echo "$rc" > positive.rc
ok=1
[[ "$rc" == 0 ]] && grep -q '^STAGE_MACRO_PASS ' positive.log || ok=0
for m in 1 2 3 4; do
  set +e
  ./obj/Vtb +mutant="$m" > "mutant_$m.log" 2>&1
  rc=$?
  set -e
  echo "$rc" > "mutant_$m.rc"
  { [[ "$rc" != 0 ]] && grep -q '^STAGE_MACRO_FAIL ' "mutant_$m.log"; } || ok=0
done
echo "GATE_OK=$ok"
[[ "$ok" == 1 ]]
