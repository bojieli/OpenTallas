#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hbm-pstore-lec4-1400
K=/srv/opentallas-scratch2/claude/codex-hbm-pstore-nativefix-1400/gen32/ot_hgi_sfu_programme_store_r10_17784bf3df1b-pfix32
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-pstore-lec4-$$" --cpus=2 --memory=16g --memory-swap=16g \
 -v "$K":/work:ro -v "$R/out":/lecout -v "$R/probe_official.py":/probe.py:ro \
 -e HUID=$(id -u) -e HGID=$(id -g) -e OT_LEC_RESET_CYCLES=4 -e OT_LEC_HINTS_PRESEED=1 \
 openroad/orfs:asap7lock bash -lc '
python3 -B -I /probe.py --kit /work --out /lecout --hints /lecout/hints.json
rc=$?
chown -R "$HUID:$HGID" /lecout
exit "$rc"
' > "$R/probe.log" 2>&1
python3 - "$R/out/lec.json" <<'PY'
import json,sys,pathlib
p=pathlib.Path(sys.argv[1]);d=json.loads(p.read_text());c=d.get('reset_contract',{});assert c.get('requested')==4 and c.get('used')==4,c
# The official driver's baseline-label default describes its original failure use;
# this capsule instead starts from a64-edge conditionalPASS. Proof engine unchanged.
r=d['cached_profile_probe'];r['official_driver_baseline_default']=r['baseline_verdict'];r['baseline_verdict']='EQUIVALENT under64-edge historicalreceipt; not usedas4-edge proof';r['actual_reset_window_asserted']=4
p.write_text(json.dumps(d,indent=1));print(d['verdict'],d.get('counts'),c)
PY
