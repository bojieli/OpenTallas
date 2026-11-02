#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-native-mixed-0130
OLD=/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2
B=/srv/opentallas-scratch2/claude/codex-ds-bf-1131/source
cd "$R"
unset OT_XS_GB_PROVIDER_UNDER_TEST
for label in programme wrong_class_programme; do
 seq=0,106,0; [ "$label" = programme ] || seq=0,0,0
 python3 prepare_native_go_provider.py --source "$B" --field "$OLD/field" --fixture "$OLD/fixture" --gb-source "$OLD/src/rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv" --phase-sequence "$seq" --period 512 --out "$R/$label"
done
python3 - <<'PY'
from pathlib import Path
import json
r=Path('.');old=Path('/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2')
for label in ['programme','wrong_class_programme']:
 for d in ['old','advance1']:
  for elem in ['e0','e0b']:
   for bank in range(2):
    p=old/'field/images'/f'u_f_0L01_{elem}_{bank}.viamap.hex'
    (r/label/d/f'u_f_0L01.u_r0.u_{elem}_{bank}.viamap.hex').symlink_to(p)
(r/'independent_gold.json').symlink_to(old/'independent_gold.json')
p=json.loads((r/'programme/programme.json').read_text());(r/'T').write_text(str(max(v['end']for v in p['programmes'].values())+600))
PY
T=$(cat T)
for spec in original_direct:programme/old:0:0 current_direct:programme/advance1:1:0 wrong_class:wrong_class_programme/advance1:1:0 wrong_date:programme/old:1:0 wrong_tag:programme/advance1:1:1; do
 IFS=: read -r name images gb bad <<< "$spec"
 "$OLD/obj/Vtb_native_go_pair" +OT_ROM_DIR="$R/$images" +T="$T" +gb="$gb" +fix_tag=0 +bad_tag="$bad" > "$name.log" 2>&1
done
