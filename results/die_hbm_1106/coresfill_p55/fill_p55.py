#!/usr/bin/env python3
"""d44v part 55: pin tables the plan names but d44v/cores does not hold (they sat only in d35a/d35b/d35c, so a plan dir
materialized from d44v alone fails views_b2r2 / reset_tree on q_b000 etc.). Additive, no die_plan change. Idempotent; run from the repo root."""
import gzip, hashlib, json, pathlib, shutil
POR = pathlib.Path("physical/die_plan/hbm/plan_of_record")
D = POR / "d44v"
def load(p): return json.load(gzip.open(p)) if p.suffix == ".gz" else json.load(open(p))
plan = load(D / "die_plan.json.gz")
refs = set()
def walk(o):
    if isinstance(o, dict):
        if isinstance(o.get("pins_file"), str): refs.add(o["pins_file"])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(plan)
sums = (D / "SHA256SUMS").read_text().splitlines()
have = {l.split()[1] for l in sums}
n = 0
for pf in sorted(refs):
    if (D / pf).exists() or (D / (pf + ".gz")).exists(): continue
    src = None
    for parent in ("d35a", "d35b", "d35c"):
        for s in (pf + ".gz", pf):
            if (POR / parent / s).exists(): src = (POR / parent / s, s); break
        if src: break
    assert src, pf
    shutil.copyfile(src[0], D / src[1])
    raw = gzip.open(src[0]).read() if src[1].endswith(".gz") else open(src[0], "rb").read()
    assert pf not in have, pf
    sums.append(hashlib.sha256(raw).hexdigest() + "  " + pf); n += 1
    print("FILLED", pf, "from", src[0].parent.parent.name)
(D / "SHA256SUMS").write_text("\n".join(sums) + "\n")
print("filled", n, "of", len(refs))
