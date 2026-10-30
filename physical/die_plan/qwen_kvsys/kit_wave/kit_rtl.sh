#!/bin/bash
# KV kit-wave kit-rtl (script mode; DIE-KV-47-SD 10-30): bind.py kit-rtl from the KV strict bind of record, then -- only
# for a plan type whose contents declare a fixed-W x6 SerDes PHY physical master (kv3_sys_SD / kv3_sys_SD_v1) --
# tools/die_plan/specialize_serdes_phy.py on the kit RTL with the plan's own declared view root, so gen.py phys finds the
# LEF master (KIT-WAVE ORD-2013: '$paramod\ot_qfd_serdes_112g_x6_phy\W=522 not found').  Every other type = the plain
# kit-wave 'bind' mode command, byte-identical.
# env TYPE/OUT/PLAN (kit_wave.py script mode, cwd = wave source checkout); KV_BIND_OUT (strict bind of record of PLAN,
# bind_report errors 0) and KV_ASBUILT (its recipe) are required (set by the per-event wrapper named in kit_wave.json).
set -euo pipefail
: "${TYPE:?}" "${OUT:?}" "${PLAN:?}" "${KV_BIND_OUT:?KV_BIND_OUT = strict bind of record}" "${KV_ASBUILT:?KV_ASBUILT = bind recipe}"
python3 -I - "$KV_BIND_OUT" "$PLAN" "$TYPE" <<'PY'
import json, sys
from pathlib import Path
b, plan, typ = sys.argv[1:]
r = json.loads((Path(b) / "bind_report.json").read_text()); e = r["errors"]
assert (len(e) if isinstance(e, list) else e) == 0, "KV_KIT_RTL: strict bind errors"
assert typ in json.loads(Path(plan).read_text())["partition_types"], "KV_KIT_RTL: unknown plan type"
PY
mkdir -p "$OUT"
python3 tools/die_plan/bind.py kit-rtl "$PLAN" --out "$KV_BIND_OUT" --asbuilt "$KV_ASBUILT" --type "$TYPE" --kit "$OUT"
VIEWS=$(python3 -I - "$PLAN" "$TYPE" <<'PY'
import json, os, sys
p = json.load(open(sys.argv[1]))["partition_types"][sys.argv[2]]
v = sorted({os.path.dirname(os.path.dirname(c["lef"])) for c in p.get("contents", [])
            if str(c.get("physical_master", "")).startswith("ot_qfd_serdes_112g_x6_phy_w") and c.get("lef")})
assert len(v) <= 1, v
print(v[0] if v else "")
PY
)
if [ -n "$VIEWS" ]; then
  python3 tools/die_plan/specialize_serdes_phy.py "$OUT" "$VIEWS" > "$OUT/specialize_serdes_phy.json"
  echo "KV_KIT_RTL PASS $TYPE + specialize_serdes_phy ($VIEWS)"
else
  echo "KV_KIT_RTL PASS $TYPE"
fi
