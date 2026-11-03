#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-post-0355
python3 - "$D" <<'PY'
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);b=k/'run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base'
paths=[k/'constraint.sdc',k/'config.mk']+[b/n for n in ('6_final.odb','6_final.spef','6_final.v','1_2_yosys.v')]
r={str(p.relative_to(k)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(k/'POST_ONLY_INPUTS.json').write_text(json.dumps(r,indent=2)+'\n')
PY
bash "$D/run_kit_kv.sh" "$D" post 16 4 > "$D/native_post_fixed.log" 2>&1
