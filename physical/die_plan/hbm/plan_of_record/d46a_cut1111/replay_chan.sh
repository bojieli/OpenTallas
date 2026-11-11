#!/bin/bash
# hbm-channels-1111 replay (DO_NOT_COUNT): re-applicable delta on plan_p11t_taps_cyc 29333b2b.
#   replay_chan.sh BASE_PLAN_DIR OUT_DIR REPO [BOUND_RTL_DIR]
# Sections (mk_chan_event.py): F L8008 strict re-station q_su00pv1 x6 + q_b113 x5 | A SU-CHAN q_su11/pv1 q_su01/pv1 | B b-type E-street stations + straight L51x4/L51x5 |
# C kv_line south grow (+pins file, clock_entries) | D q_mcb -> q_mcb_ne/q_mcb_nw | E root u_tkm_SW_root reset source note |
# cycles: ft station +1 lanes + L5090/L5091 fixed_cycles (latency.lanes keeps param).
# Then compiler_core_delta.json pending entry (ccd_pending.py) and core_conns.json regen (core_conns_batch.py trace, then cc_merge.py with the base sidecar).
# Expected die_plan.json sha256 1a1647f7c2e15b36285007048a7d586292dbebaf3f3cd5c740f31d0f5236ddb8.
set -euo pipefail
BASE=$1; OUT=$2; REPO=$3; RTL=${4:-}
H=$(cd "$(dirname "$0")" && pwd)
[ "$(sha256sum "$BASE/die_plan.json" | cut -d' ' -f1)" = 29333b2b19c992511d31720f0b80ae1c7fe4021036a59b0fd417f950b42162d1 ] || { echo BASE_SHA_FAIL; exit 7; }
mkdir -p "$OUT"; cp -a "$BASE/." "$OUT/"; chmod -R u+w "$OUT"
# rev 3 (DIE-HBM-98 11-11): L8008 x6 on q_su00__physical_v1 and x5 on q_b113 re-stationed strictly, x2 on q_su11pv1 hand-sited (hops <= 405, counts kept)
export CHAN_EXTRA_SLOTS=${CHAN_EXTRA_SLOTS-q_su00__physical_v1:L8008x6,q_b113:L8008x5}
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
  python3 -I "$H/core_conns_batch.py" "$OUT/die_plan.json" "$OUT/cc_picks.json" "$OUT/core_conns.traced.json"
  # traced wires 281/2553 cores (split hierarchies trace as {}): merge per core with the base sidecar (stale refs dropped)
  python3 -I "$H/cc_merge.py" "$OUT/die_plan.json" "$OUT/core_conns.traced.json" "$BASE/core_conns.json" "$OUT/core_conns.json"
  gzip -n -c "$OUT/core_conns.json" > "$OUT/core_conns.json.gz"
fi
sha256sum "$OUT/die_plan.json"
