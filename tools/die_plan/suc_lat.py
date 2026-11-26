"""QC-INT-R2-SUC: regenerate raw+folded latency packages for the su_c candidate and emit the explicit delta list vs C9.
usage: suc_lat.py RT BASE_TREE C9_PLAN CAND_PLAN OUTDIR"""
import json, sys
from pathlib import Path
rt, base, c9p, cp, out = map(Path, sys.argv[1:])
sys.path.insert(0, str(rt/"tools/die_plan"))
import gen, r8, schema
rd = lambda p: json.loads(Path(p).read_bytes())
W = Path("/srv/opentallas-scratch2/claude/QC-C1Q-CUT/successor_1126/whole_join")
asb = rd(base/"physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_c1p_1125.json")
pinned = W/"full_source_gate/.cow-upper"
inputs = [pinned/asb["land_r8"], *[base/x for x in asb["land_r8_extra"]]]
members = {row["id"]: row for row in rd(inputs[0])["members"]}
for p in inputs[1:]:
    members.update({row["id"]: row for row in rd(p)["members"] if not row["id"].startswith("INNER:")})
res = {}
for tag, plan in (("c9", c9p), ("cand", cp)):
    raw = rd(plan)
    lanes = schema.Plan(raw).lanes
    fold, unused = r8.lane_fold(members.values(), lanes)
    d = out/tag; d.mkdir(parents=True, exist_ok=True)
    rt_, rsv, rjs = gen.write_latency(raw, d/"raw")
    ft_, fsv, fjs = gen.write_latency(raw, d/"folded", r8_fold=fold)
    res[tag] = (rt_, ft_)
delta = []
for i, name in ((0, "raw"), (1, "folded")):
    a, b = res["c9"][i], res["cand"][i]
    assert set(a) == set(b)
    for l in sorted(a):
        ch = {k: (a[l][k], b[l][k]) for k in a[l] if a[l][k] != b[l].get(k)}
        if ch: delta.append(dict(table=name, lane=l, param=b[l].get("param"), changes=ch))
(out/"latency_delta.json").write_text(json.dumps(delta, indent=1))
print("DELTA_LANES", len(delta))
for d in delta[:40]: print(d)
