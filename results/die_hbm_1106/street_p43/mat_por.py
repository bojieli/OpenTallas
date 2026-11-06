#!/usr/bin/env python3
"""materialize the d44v POR plan (d35a/b/c + d44v overlays on d44v_por, as release_tree_plan / G0C) into OUT_DIR;
prints the por__die_plan.json path.   mat_por.py REPO OUT_DIR"""
import gzip, pathlib, shutil, sys
R, O = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
src = R / "physical/die_plan/hbm/plan_of_record"
base = O / "physical/die_plan/hbm/plan_of_record/d44v_por"
base.mkdir(parents=True, exist_ok=True)
for ov in ["d35a", "d35b", "d35c", "d44v"]:
    od = src / ov
    for f in sorted(od.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(od).as_posix(); rel = rel[:-3] if rel.endswith(".gz") else rel
        if rel in ("die_plan.json", "SHA256SUMS"):
            continue
        t = base / rel; t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(gzip.decompress(f.read_bytes()) if f.name.endswith(".gz") else f.read_bytes())
(base / "por__die_plan.json").write_bytes(gzip.decompress((src / "d44v/die_plan.json.gz").read_bytes()))
print(base / "por__die_plan.json")
