#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2
OLD=/srv/opentallas-scratch2/claude/codex-ds-native-go-2310/retry3/obj
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
# Only generic runtime objects, identical installed tool/flags; no old model/PCH/library reuse.
for stem in verilated verilated_timing verilated_threads; do
 if [ -f "$OLD/$stem.o" ] && [ -f "$OLD/$stem.d" ] && ! grep -q 'Vtb_native_go_provider' "$OLD/$stem.d"; then
  cp -p "$OLD/$stem.o" "$OLD/$stem.d" "$R/obj/"
 fi
done
/usr/bin/time -v -o backend.time make -C obj -f Vtb_native_go_pair.mk -j2 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > backend.log 2>&1
T=$(python3 -c 'import json;print(max(v["end"] for v in json.load(open("programme/programme.json"))["programmes"].values())+600)')
for spec in original_direct:old:0:0:0 current_direct:advance1:1:0:0 counterfactual_retime:advance1:1:1:0 wrong_date:old:1:0:0 wrong_tag:advance1:1:0:1; do
 IFS=: read -r name images gb fix bad <<< "$spec"
 "$R/obj/Vtb_native_go_pair" +OT_ROM_DIR="$R/programme/$images" +T="$T" +gb="$gb" +fix_tag="$fix" +bad_tag="$bad" > "$name.log" 2>&1
done
printf 'FULL_PAIR_RUNS_COMPLETE\n' > status
