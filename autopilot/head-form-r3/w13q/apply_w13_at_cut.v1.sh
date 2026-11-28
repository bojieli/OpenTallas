#!/bin/bash
# HEAD-FORM-R3: stock atomic apply of W13q at the 21:00 PST 11-27 cut (apply_w12_at_cut.sh pattern).
set -euo pipefail
D=/srv/opentallas-scratch2/claude
C=$HOME/coord
P=$C/autopilot/head-form-r3/w13q
R=$D/rt/b71c5218e0b5
export TZ=America/Los_Angeles
[[ $(date +%F) == 2026-11-27 && $(date +%H%M) -ge 2100 ]] || { echo "The scheduled W13 cut time has not been reached on the cut date." >&2; exit 64; }
for v in "$P/VERDICT_w13_noeast_4fca0de51ee0.txt" "$P/VERDICT_pinreg_41e860a82c5f.txt"; do
  head -1 "$v" | grep -qxE "VERDICT: (GOOD|GOOD-WITH-WATCH)" || { echo "review verdict not GOOD/GOOD-WITH-WATCH: $v" >&2; exit 65; }
  ! grep -q "BLOCKING" "$v" || grep -qi "none BLOCKING\|0 BLOCKING\|no blocking\|nothing.*block" "$v" || { echo "blocking finding in $v" >&2; exit 65; }
done
python3 -I -B - "$P/permit/candidate.json" "$C/autopilot/kit_wave.json" <<PY
import json,sys
from pathlib import Path
candidate,live=map(Path,sys.argv[1:])
obj=json.loads(candidate.read_bytes()); m=obj["marker"]; cfg=m["config"]
assert m["plan_sha256"]=="148712eff5f7c79cd1d6eb162597fda6279f3edc857b6a8841bb9f81ef382fa7"
assert m["src_manifest_sha"]=="43a45f752d5fec4f5d1d597e56ffaabe45d90eec944b0851d80068a9dd0f524d"
assert m["tools_sha"]=="b71c5218e0b5f4acad7d41c239464bb36c1eaf0d"
assert m["tree"]=="/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18w13q_1127"
assert len(cfg["only_items"])==17 and "hd_mesh" not in cfg["only_items"]
assert cfg["review_before_route"]=={"event":"head_rp21z20NF15f_r18w13q_1127","all_items":True,"required":True}
assert {h["id"] for h in obj["hold_records_add"]}=={"HEAD-W13-ROUTE-HD-HOST-E-PINREG","HEAD-W13-ROUTE-HD-CTL-PINREG"}
old=json.loads(live.read_bytes())["dies"]["s81_head"]
assert old["event"]=="head_rp21z20NF15f_r18w12_1126",old["event"]
assert old["src"]=="/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18w12_1126",old["src"]
assert len(old.get("hold_records") or [])>=16
PY
exec python3 -I -B "$R/tools/autopilot/publish_apply.py" apply \
   --candidate "$P/permit/candidate.json" \
   --expect-source "$D/kw45/snap_s81_head/s81_head_r18w12_1126" \
   --expect-event head_rp21z20NF15f_r18w12_1126 --lane head-form-r3 --coord "$C" \
   --no-post-bind \
   --allow-no-post-bind "Exact sealed W13q source 43a45f752d5f: strict bind 48 jobs (8338 inst, 0 unbound), cohort 27/27, LAT334, native release, PRE 0 and G0 0 errors all passed on the same source plan 148712eff5f7 and rt b71c5218e0b5 at epyc12:$D/HEAD-INT-R3/form/gate_w13q_b71c/summary.json; script export uses this exact source and no bind-out posthook."
