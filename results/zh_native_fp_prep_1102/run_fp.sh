#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-zh-native-fp-prep-0705
python3 "$R/guard.py" "$R"
python3 - "$R" <<'PY'
from pathlib import Path
import sys,json,hashlib
r=Path(sys.argv[1]);d=json.loads((r/'DRY_GUARD.json').read_text());assert d['status']=='PASS_NORMAL_DRY_STAGE2_ONLY'
for n in ('EXPECTED.json','inside_fp.sh','run_dry.sh'):
 assert hashlib.sha256((r/n).read_bytes()).hexdigest()==d['hashes'][n],n
PY
docker run --rm --name "codex-zh-fp-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work -v "$R":/case:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /case/inside_fp.sh run
python3 - "$R" <<'PY'
from pathlib import Path
import hashlib,json,sys
r=Path(sys.argv[1]);d=json.loads((r/'EXPECTED.json').read_text());k=r/'kit'
for rel,h in d['expected'].items():assert hashlib.sha256((k/rel).read_bytes()).hexdigest()==h,rel
b=k/'run/results/asap7/hc_ot_nhb_zh__151_2x151_2/base'
assert (b/'2_floorplan.odb').is_file() and (b/'2_floorplan.sdc').is_file()
assert not any(p.name.startswith(('3_','4_','5_','6_')) for p in b.iterdir())
print('PASS_POST_FP exact89inputs unchanged/native2_floorplan present/no stage3+')
PY
