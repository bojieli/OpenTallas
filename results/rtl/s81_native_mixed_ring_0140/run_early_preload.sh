#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140/retry3_early_preload
BASE=/srv/opentallas-scratch2/claude/codex-ds-native-ring-0140/retry2
OLD=/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2
MIX=/srv/opentallas-scratch2/claude/codex-ds-native-mixed-0130
B=/srv/opentallas-scratch2/claude/codex-ds-bf-1131/source
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
ln -s "$OLD/independent_gold.json" independent_gold.json
for label in programme wrong_class_programme; do
 cp -a "$MIX/$label" "$R/$label"
 python3 prepare_native_ring_fixture.py --programme "$R/$label" --fixture "$OLD/fixture" --source "$B"
done
T=$(python3 -c 'import json;print(max(v["end"] for v in json.load(open("programme/programme.json"))["programmes"].values())+600)')
for spec in original_direct:programme/old:0:0 current_direct:programme/advance1:1:0 wrong_class:wrong_class_programme/advance1:1:0 wrong_date:programme/old:1:0 wrong_tag:programme/advance1:1:1; do
 IFS=: read -r name images gb bad <<< "$spec"
 "$BASE/obj/Vtb_native_go_pair" +OT_ROM_DIR="$R/$images" +T="$T" +gb="$gb" +fix_tag=0 +bad_tag="$bad" +ring=1 > "$name.log" 2>&1
done
python3 check_native_go_mixed.py --root "$R" --field "$OLD/field" --out "$R/checked"
