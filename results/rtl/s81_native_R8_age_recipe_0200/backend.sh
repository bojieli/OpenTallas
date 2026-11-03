#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-r8-0200
OLD=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140/retry2/obj
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
for stem in verilated verilated_timing verilated_threads; do
 if [ -f "$OLD/$stem.o" ] && [ -f "$OLD/$stem.d" ] && ! grep -q Vtb_native_go_pair "$OLD/$stem.d"; then cp -p "$OLD/$stem.o" "$OLD/$stem.d" obj/; fi
done
/usr/bin/time -v -o backend.time make -C obj -f Vtb_native_go_pair.mk -j2 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > backend.log 2>&1
T=$(python3 -c 'import json;print(max(v["end"] for v in json.load(open("programme/programme.json"))["programmes"].values())+600)')
for spec in uniform_original:old:0:0:0 uniform_current:advance1:1:0:0 asbuilt_original:old:0:1:0 asbuilt_current:advance1:1:1:0 wrong_lane:advance1:1:2:0 wrong_date:old:1:0:0 wrong_tag:advance1:1:0:1; do
 IFS=: read -r name images gb mode bad <<< "$spec"
 "$R/obj/Vtb_native_go_pair" +OT_ROM_DIR="$R/programme/$images" +T="$T" +gb="$gb" +transport_mode="$mode" +fix_tag=0 +bad_tag="$bad" +ring=1 > "$name.log" 2>&1
done
python3 check_native_go_r8.py --root "$R" --out "$R/checked"
