"""DIE-KV-61 11-02: pin the frozen KV reset relay obstacle model (metadata-only plan event).

main 74080dbb8 (canonical placed obstacle union for reset relays) re-solves every KV soft type's reset
relay graph; the published landing collector_tree snapshots no longer match and strict bind FAILS
("EMIT collector rst_rl_68: raw reset parent rst_rl_63 absent", kv3_hg). The frozen plan keeps the
relay graph it was solved, landed and G0C'd with: every non-hard KV type gets
reset.obstacle_model = "lef_origin". No geometry, pin, net or relay changes.
Census vs canonical union (rtobs_1102/census.json): 5859 published relays, 4 inside a soft reuse-leaf
body (no LEF, std-cell placeable region), 0 inside a hard core / LEF'd macro.
"""
import json, sys
from pathlib import Path
p = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "plan_c.json")
P = json.loads(p.read_text()); n = 0
for tn, t in P["partition_types"].items():
    if t.get("hard"):
        continue
    r = t.setdefault("reset", {})
    if r.get("obstacle_model") != "lef_origin":
        r["obstacle_model"] = "lef_origin"; n += 1
p.write_text(json.dumps(P, indent=1) + "\n")
print("types pinned", n)
