#!/usr/bin/env python3
"""Re-run route_supply.py after every plan event and append to the FLAGS TSV (PLAN-ROUTE-1; ADVISORY, never a gate).

Reads the plans of record as JSON lines on stdin (or --plans FILE):
  {"die": "s81", "plan": "physical/die_plan/s81/plan_h2_2249.json", "refs": ["s81_head/plan_of_record/l48uo", ...]}
(the PLANS table of release_tree_plan.py, refs relative to physical/die_plan).  A die is re-run when its plan file
sha256 differs from the newest plan_sha of that die in the TSV (or with --force); results are appended through
route_supply_flags.py.  Exits 0 always; prints one line per die.

  route_supply_watch.py --repo REPO --tsv FLAGS.tsv --out-root DIR [--release-cache J] [--stamp S] [--force] < plans

--grt-halving edge [--grt-edge-gcells K] models the GRT-PATCH-1 patched OpenROAD image (default: stock, full); keep
one TSV per image, since a die is skipped when its plan sha is already in the TSV.
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import route_supply_flags as F  # noqa: E402


def run_die(repo, p, out, cache, grt=("full", 2)):
    cmd = [sys.executable, "-I", str(HERE / "route_supply.py"), str(repo / p["plan"]), "--die", p["die"],
           "--repo", str(repo), "--out", str(out)]
    refs = list(p.get("refs") or []) + [p["die"]]
    cmd += ["--ref-dirs"] + refs
    if cache:
        cmd += ["--release-cache", cache]
    cmd += ["--grt-halving", grt[0], "--grt-edge-gcells", str(grt[1])]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return p["die"], r.returncode, (r.stderr.strip().splitlines() or [""])[-1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--tsv", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--plans")
    ap.add_argument("--release-cache")
    ap.add_argument("--stamp")
    ap.add_argument("--main", default="-")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--grt-halving", choices=("full", "edge", "none"), default="full")
    ap.add_argument("--grt-edge-gcells", type=int, default=2)
    a = ap.parse_args(argv)
    repo = Path(a.repo)
    src = open(a.plans) if a.plans else sys.stdin
    plans = [json.loads(x) for x in src if x.strip()]
    seen = F.last_shas(a.tsv)
    todo = []
    for p in plans:
        pp = repo / p["plan"]
        if not pp.exists():
            print(f"{p['die']}: plan {p['plan']} missing in repo, skipped")
            continue
        s = F.sha(pp)
        if not a.force and seen.get(p["die"]) == s:
            print(f"{p['die']}: plan {s} unchanged")
            continue
        todo.append((p, s))
    if not todo:
        return 0
    stamp = a.stamp or F.datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    if a.grt_halving != "full":
        stamp += " grt=" + a.grt_halving + (f"K{a.grt_edge_gcells}" if a.grt_halving == "edge" else "")
    grt = (a.grt_halving, a.grt_edge_gcells)
    out = Path(a.out_root) / stamp.replace(" ", "_").replace(":", "")
    out.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=len(todo)) as ex:
        res = list(ex.map(lambda t: run_die(repo, t[0], out, a.release_cache, grt), todo))
    for die, rc, last in res:
        print(f"{die}: re-run rc={rc} {last}")
    F.main([str(out), "--tsv", a.tsv, "--stamp", stamp, "--main", a.main,
            "--plans"] + [f"{p['die']}={repo / p['plan']}" for p, _ in todo])
    return 0


if __name__ == "__main__":
    sys.exit(main())
