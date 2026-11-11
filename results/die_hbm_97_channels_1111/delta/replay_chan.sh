#!/bin/bash
# hbm-channels-1111 replay (DO_NOT_COUNT): re-applicable delta on plan_p11t_taps_cyc 29333b2b.
#   replay_chan.sh BASE_PLAN_DIR OUT_DIR REPO [BOUND_RTL_DIR]
# Sections (mk_chan_event.py): A SU-CHAN q_su11/pv1 q_su01/pv1 | B b-type E-street stations + straight L51x4/L51x5 |
# C kv_line south grow (+pins file, clock_entries) | D q_mcb -> q_mcb_ne/q_mcb_nw | E root u_tkm_SW_root reset source note |
# cycles: ft station +1 lanes + L5090/L5091 fixed_cycles (latency.lanes keeps param).
# Then compiler_core_delta.json pending entry (ccd_pending.py) and core_conns.json regen (core_conns_batch.py, no --base).
# Expected die_plan.json sha256 fd5123010508864c82549536c8a04b4db9bc826cd60b945384f3f489c9c3e02a.
set -euo pipefail
BASE=$1; OUT=$2; REPO=$3; RTL=${4:-}
H=$(cd "$(dirname "$0")" && pwd)
[ "$(sha256sum "$BASE/die_plan.json" | cut -d' ' -f1)" = 29333b2b19c992511d31720f0b80ae1c7fe4021036a59b0fd417f950b42162d1 ] || { echo BASE_SHA_FAIL; exit 7; }
mkdir -p "$OUT"; cp -a "$BASE/." "$OUT/"; chmod -R u+w "$OUT"
T=$(mktemp -d); python3 -I "$H/mk_chan_event.py" "$BASE/die_plan.json" "$T" "$REPO"
cp "$T/die_plan.json" "$T/channels_1111_event.json" "$T/clock_entries.json" "$OUT/"; cp -r "$T/cores/." "$OUT/cores/"
gzip -n -c "$OUT/clock_entries.json" > "$OUT/clock_entries.json.gz"; rm -rf "$T"
python3 -I "$H/ccd_pending.py" "$OUT"
if [ -n "$RTL" ]; then
  python3 -I - "$OUT/die_plan.json" "$RTL" "$OUT/cc_picks.json" <<'PY'
import json, os, sys
p = json.load(open(sys.argv[1])); B = sys.argv[2]; picks = {}
for t, v in p["partition_types"].items():
    if not v.get("hard_cores"): continue
    f = [x for x in (v["module"] + "__" + t + ".sv", v["module"] + ".sv") if os.path.exists(os.path.join(B, x))]
    assert f, t; picks[t] = os.path.join(B, f[0])
json.dump(picks, open(sys.argv[3], "w"), indent=1)
PY
  python3 -I "$H/core_conns_batch.py" "$OUT/die_plan.json" "$OUT/cc_picks.json" "$OUT/core_conns.json"
  gzip -n -c "$OUT/core_conns.json" > "$OUT/core_conns.json.gz"
fi
sha256sum "$OUT/die_plan.json"
