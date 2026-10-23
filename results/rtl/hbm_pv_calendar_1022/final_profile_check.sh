#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/hbm-pv-calendar-1022
python3 final_profile_check.py > profile_validation.json
PYTHONPATH=repo/tools python3 -m hbm_layer_vehicle.layer_images --design ds --layer 0 --priced priced_layers.json --boundary /srv/opentallas-scratch/claude/hbmc-token2/pv_r18_probe/slice/boundary.json --fixtures fixture --records 20,21,23 --su-lower2 --native-read-return 18 --native-write-return 15 --rf-local 1 --su-pretree-profile pretree_profile_final.json --out reemit77final > reemit77final.log 2>&1
cmp reemit77v2/images/su_prog00/quarter.mem reemit77final/images/su_prog00/quarter.mem
cmp reemit77v2/images/su_prog00/cols/config.mem reemit77final/images/su_prog00/cols/config.mem
python3 - <<'PY' > source_comparison.json
import json,hashlib
from pathlib import Path
p=Path('.')
out=[]
for i in [20,21,23]:
 a=json.loads((p/f'r{i:03d}_su/record.json').read_text());b=json.loads((p/f'reemit77final/images/r{i:03d}_su/record.json').read_text())
 key=lambda x:{(tuple(e['words']),e['mask']):e['value'] for e in x['expect']}
 assert key(a)==key(b),(i,'arithmetic/check mask changed')
 assert a['data']==b['data'],(i,'input words changed')
 out.append(dict(record=i,expected_words_and_masks_unchanged=True,input_words_unchanged=True))
q=p/'reemit77final/images/su_prog00/quarter.mem'
print(json.dumps(dict(status='PASS',records=out,old_edges=len((p/'quarter_old.mem').read_text().split()),new_edges=len(q.read_text().split()),quarter_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),final_quarter_and_configuration_byte_identical_to_running_full_replay=True),indent=2))
PY
cat profile_validation.json source_comparison.json
