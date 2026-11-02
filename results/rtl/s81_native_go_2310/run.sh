#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-go-2310/retry3
B=/srv/opentallas-scratch2/claude/codex-ds-bf-1131
cd "$R"
python3 prepare_native_go_provider.py --source "$B/source" --field "$R/field" --fixture "$B/fixture" --gb-source "$R/src/rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv" --out "$R/programme"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-PINMISSING -Wno-MULTIDRIVEN --top-module tb_native_go_provider -Mdir "$R/obj" -f sources.f --build-jobs 2 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > build.log 2>&1
for spec in reference:old:0:1:0 current:advance1:1:0:0 candidate:advance1:1:1:0 wrong_date:old:1:1:0 wrong_tag:advance1:1:1:1; do
 IFS=: read -r name images gb fix bad <<< "$spec"
 "$R/obj/Vtb_native_go_provider" +OT_ROM_DIR="$R/programme/$images" +T=2000 +gb="$gb" +fix_tag="$fix" +bad_tag="$bad" > "$R/$name.log" 2>&1
done
printf 'NATIVE_GO_RUNS_COMPLETE\n' > status
