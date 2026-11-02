#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-bf-ranktags-2230
B=/srv/opentallas-scratch2/claude/codex-ds-bf-1131
export PYTHONPATH="$B/source/tools:$B/source/tools/s81_dv:$B/source/tools/s81_dv/layer_prog:$B/source/tools/s81"
export OT_S81_SELECTED_SOURCE_ROOT="$B/source" OT_S81_SELECTED_ASBUILT_MANIFEST=asbuilt_kva3_g3tag2_sel.json OT_XS_ASB_SCHEDULE_DIR="$B" OT_XS_GB_PROVIDER_UNDER_TEST=1 OT_XS_Q_CPR=1
cd "$R"
python3 - <<'PY'
import json,hashlib
from pathlib import Path
r=Path('.');b=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-1131');a=json.loads((r/'current_phase110.json').read_text());old=json.loads((b/'full0_source/field.json').read_text());assert a['phase']==old['phases'][110]
for name,sha in a['images_sha256'].items():
 p=b/'h10vec'/name
 assert p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
(r/'source_join.json').write_text(json.dumps(dict(status='PASS_CURRENT_CAP_SAFE_BF_SOURCE_IMAGE_JOIN',phase=110,exact_BF_images=len(a['images_sha256']),field_phase_identical=True),indent=2)+'\n')
PY
python3 tools/s81_dv/bf_asbuilt_1101/phase_vector.py --snapshot "$B/full0_source/field.json" --vector "$B/h10vec" --fixture "$B/fixture" --phase 110 --out "$R/phase110"
python3 tools/s81_dv/bf_asbuilt_1101/replay_vectors.py --vector "$R/phase110" --measurement "$B/h10x_retry3_mem8/measure.json" --out "$R/static110"
python3 tools/s81_dv/tokfunc/bf_rank_phase_overlay.py --vector "$R/static110" --field "$B/full0_source/field.json" --phase 110 --out "$R/rank110"
python3 tools/s81_dv/tokfunc/bf_rank_phase_overlay.py --vector "$R/static110" --field "$B/full0_source/field.json" --phase 110 --out "$R/wrong110" --wrong-first-tag
for name in static110 rank110 wrong110; do
 "$B/h10x_retry3_mem8/obj_static/Vtb_s81dv_frame" $(cat "$R/$name/ARGS") > "$R/$name/run.log" 2>&1
done
python3 "$B/source/tools/s81_dv/layer_prog/xs_place.py" check --dir "$R/static110" --log "$R/static110/run.log" --fixtures "$B/fixture" > "$R/static110/check.log" 2>&1
python3 - <<'PY'
import json,re
from pathlib import Path
r=Path('.');owned=json.loads((r/'current_phase110.json').read_text())['phase']['row_index']
def read(name):
 s=(r/name/'run.log').read_text();end=re.search(r'END edges=\d+ ret_words=(\d+).*? fault=(\d+) spine_fault=(\d+)',s);assert end and end.groups()==('6','0','0'),name
 return [(int(e),int(w,16)) for e,w in re.findall(r'^RET (\d+) ([0-9a-f]+)$',s,re.M)]
a=read('static110');c=read('rank110');m=read('wrong110');expected=[]
for edge,w in a:
 tag=(w>>1)&0xffffffff;local=(tag>>13)&0x3fff;newtag=(tag&~(0x3fff<<13))|(owned[local]<<13);expected.append((edge,(w&~(0xffffffff<<1))|(newtag<<1)))
assert c==expected, 'native candidate differs from exact ownership-label-only change'
assert m!=expected, 'wrong-row label control not caught'
report=dict(status='PASS_DISABLED_NATIVE_BF_NONZERO_ROW_LABEL_WITNESS',phase=110,rows=owned,returns=6,baseline_fault=0,candidate_fault=0,dates_payloads_controls_and_descriptors_unchanged=True,wrong_row_control_caught=True,expected=[[e,f'{w:017x}'] for e,w in expected],native=[[e,f'{w:017x}'] for e,w in c],production_enabled=False,added_cycles=0,scope='Exact retained BF-active/Q-idle source, single actual CAP-safe WOA phase; consuming capture contract/global mission unqualified')
(r/'check.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
PY
