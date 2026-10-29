#!/bin/bash
set -euo pipefail
BASE=/srv/opentallas-scratch2/claude/head-kits-7/serdes_qk/kits/ot_s81_kp4_dchn_head
RUN=/srv/opentallas-scratch2/claude/codex-head-serdes-lep-0825
CONTAINER=hbmcore-ot_s81_kp4_dchn_head_-1487664
mkdir -p "$RUN"
if docker inspect "$CONTAINER" >/dev/null 2>&1; then
    docker wait "$CONTAINER" > "$RUN/inherited_container_exit.txt"
fi
python3 - "$BASE" "$RUN" <<'PY'
import json,sys,hashlib
from pathlib import Path
b,r=map(Path,sys.argv[1:]); d=json.loads((b/'lec/lec.json').read_text())
receipt={k:d.get(k) for k in ('verdict','counts','reason','note','t_total_s')}
receipt['source']=str(b)
receipt['netlist_sha256']=hashlib.sha256((b/'run/results/asap7/hbc_ot_s81_kp4_dchn/base/1_2_yosys.v').read_bytes()).hexdigest()
(r/'inherited_lec_summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
if d.get('verdict')!='EQUIVALENT': raise SystemExit('STOP: strict inherited LEC did not prove EQUIVALENT; no placement submitted')
PY
test ! -e "$RUN/quarter_keep"
cp -a "$BASE" "$RUN/quarter_keep"
cmp "$BASE/run/results/asap7/hbc_ot_s81_kp4_dchn/base/1_2_yosys.v" "$RUN/quarter_keep/run/results/asap7/hbc_ot_s81_kp4_dchn/base/1_2_yosys.v"
exec /home/ubuntu/.local/bin/ot-run --mem 32 --threads 8 --dir "$RUN" -- bash "$RUN/place_serdes.sh"
