#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$D/../.." && pwd)
test -f "$D/candidate.sv" || cp "$REPO/rtl/hbm_accel/cores_split/sk_en_q4/ot_hbm_hc_tail_rest_core_ce.sv" "$D/candidate.sv"
test -f "$D/delay.sv" || cp "$REPO/rtl/hdc/ot_hdc_delay.sv" "$D/delay.sv"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style -Werror-WIDTH -Werror-SELRANGE --top-module tb_tailmax --Mdir "$D/obj" -o sim "$D/tb.sv" "$D/gold.sv" "$D/candidate.sv" "$D/mutant.sv" "$D/stubs.sv" "$D/delay.sv" > "$D/build.log" 2>&1
"$D/obj/sim" > "$D/result.log" 2>&1
cat "$D/result.log"
