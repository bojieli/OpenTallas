#!/usr/bin/env python3
"""HBM-CORES-REBAL-9: prod_compile sweep over every production SU.VOP record.
(1) default byte-identity: old prod_compile (git HEAD~ archive, BASE) vs the new one with no options -> identical dirs;
(2) per-record cycles at the lane builds as-built / WCOPY 1 / MLAT 5 / MLAT 5 + WCOPY 1 (the compiler's own schedule).
usage: pc_sweep.py WT BASE_TOOLS_ROOT OUT"""
import filecmp, json, subprocess, sys
from pathlib import Path
WT, BASE, OUT = map(Path, sys.argv[1:4])
sys.path.insert(0, str(WT / "tools/hbm_static/toksim_su/suvop"))
sys.path.insert(0, str(WT / "tools/hbm_static")); sys.path.insert(0, str(WT / "tools"))
import prod_compile as PC  # noqa: E402
NEW = WT / "tools/hbm_static/toksim_su/suvop/prod_compile.py"
OLD = BASE / "tools/hbm_static/toksim_su/suvop/prod_compile.py"
CASES = {"m4w0": [], "m4w1": ["--wcopy", "1"], "m5w0": ["--mlat", "5"], "m5w1": ["--mlat", "5", "--wcopy", "1"]}


def run(py, d, rec, extra):
    r = subprocess.run([sys.executable, str(py), str(d), rec] + extra, capture_output=True, text=True)
    if r.returncode:
        return dict(error=(r.stderr or r.stdout).strip().splitlines()[-1][:300])
    return json.loads(r.stdout.strip().splitlines()[-1])


def same_tree(a, b):
    c = filecmp.dircmp(a, b)
    if c.left_only or c.right_only or c.diff_files or c.funny_files:
        return False
    _, mism, err = filecmp.cmpfiles(a, b, c.common_files, shallow=False)
    return not mism and not err and all(same_tree(Path(a) / s, Path(b) / s) for s in c.common_dirs)


res = {}
for rec, spec in PC.RECS.items():
    mods = spec[4]
    row = dict(ci_sfu=mods.get("ci_sfu", 0), cp_m1=mods.get("cp_m1", 0), red=spec[5])
    b = run(OLD, OUT / "base" / rec, rec, [])
    for k, ex in CASES.items():
        row[k] = run(NEW, OUT / k / rec, rec, ex)
    row["default_identical"] = ("error" in b and "error" in row["m4w0"]) or same_tree(OUT / "base" / rec, OUT / "m4w0" / rec)
    if "error" not in row["m4w0"]:
        c0 = row["m4w0"]["cycles_serial"]
        row["delta"] = {k: (row[k]["cycles_serial"] - c0 if "error" not in row[k] else None) for k in CASES}
    res[rec] = row
    print(rec, row.get("delta"), "identical" if row["default_identical"] else "DIFF", flush=True)
(OUT / "pc_sweep.json").write_text(json.dumps(res, indent=1) + "\n")
print("ALL_DEFAULT_IDENTICAL", all(r["default_identical"] for r in res.values()), "records", len(res))
