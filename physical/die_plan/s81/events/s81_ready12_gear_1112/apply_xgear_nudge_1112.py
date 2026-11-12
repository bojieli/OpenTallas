#!/usr/bin/env python3
"""S81-GEAR-1 v2 (DIE-S81-87, 2026-11-12): g_gear + minimal-move ft re-site (tools/die_plan/ft_nudge.py) of chosen slots.

1. apply_xgear_1112.py (same transformation / fail-closed checks) on IN -> tmp.
2. ft_nudge.py --no-snap on tmp (in the plan dir so the geometry check finds its context) -> nudged.
3. only the ft_slots named by --only TYPE:SLOT[,..] (or all that ft_nudge changed with --all) take their bit_sites_um /
   regs_um from the nudged plan; every other byte of the gear output stays.  Station counts, windows, pins, outlines,
   cores never change (ft_nudge contract).  Fail-closed: a requested slot that ft_nudge did not change is an error
   unless it has no macro hit; a nudged slot must have the same width and station count.
usage: apply_xgear_nudge_1112.py IN OUT REPORT --delta D (--only T:S[,T:S] | --all) --repo REPO
"""
import argparse, json, os, subprocess, sys, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--delta", required=True); ap.add_argument("--repo", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--only"); g.add_argument("--all", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo); plan_dir = repo / "physical/die_plan/s81"
    tag = uuid.uuid4().hex[:10]
    tmp = Path(f"/tmp/xgn_{tag}_gear.json"); rep1 = Path(f"/tmp/xgn_{tag}_rep1.json")
    r = subprocess.run([sys.executable, "-I", str(HERE / "apply_xgear_1112.py"), a.inp, str(tmp), str(rep1), "--delta", a.delta],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("gear stage failed: " + r.stdout[-300:] + r.stderr[-600:])
    ws = plan_dir / f".xgn_{tag}_ws811.json"; nudged = Path(f"/tmp/xgn_{tag}_nudged.json"); ledger = Path(f"/tmp/xgn_{tag}_ledger.json")
    ws.write_bytes(tmp.read_bytes())
    try:
        r = subprocess.run([sys.executable, "-I", str(repo / "tools/die_plan/ft_nudge.py"), str(ws), str(nudged), str(ledger), "--no-snap"],
                           capture_output=True, text=True, cwd=repo)
    finally:
        ws.unlink()
    if r.returncode:
        sys.exit("ft_nudge failed: " + r.stdout[-300:] + r.stderr[-800:])
    G = json.loads(tmp.read_text()); N = json.loads(nudged.read_text()); led = json.loads(ledger.read_text())
    want = None if a.all else {tuple(x.split(":")) for x in a.only.split(",")}
    changed = []
    for tn, T in G["partition_types"].items():
        for s, ns in zip(T.get("ft_slots", []), N["partition_types"][tn].get("ft_slots", [])):
            if s != ns:
                if s["name"] != ns["name"] or s["width"] != ns["width"] or s.get("stations") != ns.get("stations"):
                    sys.exit(f"FAIL nudge changed shape of {tn}/{s[name]}")
                if want is None or (tn, s["name"]) in want:
                    for k in ("bit_sites_um", "regs_um"):
                        if k in ns:
                            s[k] = ns[k]
                        elif k in s:
                            del s[k]
                    changed.append([tn, s["name"]])
    if want is not None:
        missing = sorted(want - {tuple(c) for c in changed})
        if missing:
            sys.exit(f"FAIL requested slots not changed by ft_nudge (no hit?): {missing}")
    Path(a.out).write_text(json.dumps(G, indent=1))
    rep = json.loads(rep1.read_text()); rep.update(nudged_slots=changed, nudge_ledger=[x for x in led if [x["type"], x["slot"]] in changed], nudge_stdout=r.stdout[-300:])
    Path(a.report).write_text(json.dumps(rep, indent=1))
    for p in (tmp, rep1, nudged, ledger):
        p.unlink(missing_ok=True)
    print(json.dumps({"nudged": changed}))

if __name__ == "__main__":
    main()
