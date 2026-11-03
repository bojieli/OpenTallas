#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140/retry2
OLD=/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
for stem in verilated verilated_timing verilated_threads; do
 if [ -f "$OLD/obj/$stem.o" ] && [ -f "$OLD/obj/$stem.d" ] && ! grep -q Vtb_native_go_pair "$OLD/obj/$stem.d"; then
  cp -p "$OLD/obj/$stem.o" "$OLD/obj/$stem.d" obj/
 fi
done
/usr/bin/time -v -o backend.time make -C obj -f Vtb_native_go_pair.mk -j2 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0 > backend.log 2>&1
T=$(python3 -c 'import json;print(max(v["end"] for v in json.load(open("programme/programme.json"))["programmes"].values())+600)')
for spec in original_direct:programme/old:0:0 current_direct:programme/advance1:1:0 wrong_class:wrong_class_programme/advance1:1:0 wrong_date:programme/old:1:0 wrong_tag:programme/advance1:1:1; do
 IFS=: read -r name images gb bad <<< "$spec"
 "$R/obj/Vtb_native_go_pair" +OT_ROM_DIR="$R/$images" +T="$T" +gb="$gb" +fix_tag=0 +bad_tag="$bad" +ring=1 > "$name.log" 2>&1
done
python3 check_native_go_mixed.py --root "$R" --field "$OLD/field" --out "$R/checked"
