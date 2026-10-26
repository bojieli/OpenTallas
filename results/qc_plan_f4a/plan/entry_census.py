# QC-PLAN-F4A ruling (3) census: --entries xy vs current-outline centre (4.32 lattice) for every hard core of a plan
import sys, json
from pathlib import Path
W = sys.argv[1]; sys.path.insert(0, W + "/tools/die_plan")
import master_plan as M, schema as S
for plan, ent in zip(sys.argv[2::2], sys.argv[3::2]):
    P = S.Plan(S.load(plan), Path(plan)); E = json.loads(Path(ent).read_text())
    mods = {}
    for tn, t in P.types.items():
        for h in t.get("hard_cores", []):
            mods.setdefault(h["module"], h)
    diff = []
    for m, h in mods.items():
        c = (M.snap(h["outline_um"][0] / 2), M.snap(h["outline_um"][1] / 2))
        e = (E.get(m) or {}).get("xy")
        if e and abs(e[0] - c[0]) + abs(e[1] - c[1]) > 1e-6:
            diff.append((m, h["outline_um"], list(c), e))
    print(plan.split("/")[-1], "cores", len(mods), "with_entries", sum(1 for m in mods if (E.get(m) or {}).get("xy")), "differ", len(diff))
    for d in diff[:12]: print("  ", d)
