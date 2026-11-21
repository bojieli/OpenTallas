#!/usr/bin/env python3
"""R8-REFRESH (QC-PLAN-R8 11-21, COORD: R8_STALE hit QC V2, KV D27c and sle variant B -> one class): refresh the R8 landing
table AND every asbuilt land_r8_extra table from a bind's bus_groups.json, so a re-bind never runs on a stale table.

  1 derive   land_r8_derive.py derive PLAN BUS_GROUPS --like TABLE --out TABLE [--pin-pre PRE --pin-extra N]
             (the QC s29 deliberate pin rides along when --pin-pre is given; same call as qc_r8_pinned.sh)
  2 extras   each table in asbuilt.land_r8_extra is AUTHORITATIVE over the derived table in the bind (Binder.load_r8); a member
             whose id is in the fresh derivation takes its bound/landed from it, its pad and every other field stay
             (tree-align pads are the extra table's own content).  INNER:* members are left alone.
Tables are replaced via tmp + rename.  Exit 0 = refreshed; the summary line names members changed per table.

Use it between a bind that reported R8_STALE and the re-bind (see bind_r8_loop in the die bind scripts):
  python3 -I tools/die_plan/r8_refresh.py PLAN BIND_OUT/bus_groups.json TABLE --asbuilt ASBUILT [--pin-pre PRE] [--pin-extra N]
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rebound_extra(derived, extra):
    """derived/extra: table dicts. Returns (new extra dict, changed count, {delta: n})."""
    D = {m["id"]: m for m in derived["members"]}
    X = json.loads(json.dumps(extra)); n = 0; delta = {}
    for m in X["members"]:
        if m["id"].startswith("INNER:"):
            continue
        t = D.get(m["id"])
        if t is None or (m.get("bound"), m.get("landed")) == (t["bound"], t["landed"]):
            continue
        k = t["bound"] - m["bound"]; delta[k] = delta.get(k, 0) + 1
        m["bound"], m["landed"] = t["bound"], t["landed"]; n += 1
    return X, n, delta


def _write(path, obj):
    tmp = path.with_name(path.name + ".r8refresh.tmp")
    tmp.write_text(json.dumps(obj, indent=1)); os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("plan"); ap.add_argument("bus_groups"); ap.add_argument("table")
    ap.add_argument("--asbuilt", required=True, help="asbuilt json (its land_r8_extra list, paths relative to --root)")
    ap.add_argument("--root", default=".", help="tree root the asbuilt paths are relative to (default: cwd)")
    ap.add_argument("--pin-pre"); ap.add_argument("--pin-extra")
    A = ap.parse_args(argv)
    cmd = [sys.executable, "-I", str(HERE / "land_r8_derive.py"), "derive", A.plan, A.bus_groups, "--like", A.table, "--out", A.table]
    if A.pin_pre:
        cmd += ["--pin-pre", A.pin_pre] + (["--pin-extra", A.pin_extra] if A.pin_extra is not None else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout[-2000:]); sys.stderr.write(r.stderr[-4000:])
    if r.returncode:
        print(f"R8_REFRESH FAIL derive rc {r.returncode}"); return r.returncode
    derived = json.loads(Path(A.table).read_text())
    root = Path(A.root)
    extras = json.loads(Path(A.asbuilt).read_text()).get("land_r8_extra", [])
    summary = {}
    for xf in extras:
        p = Path(xf) if Path(xf).is_absolute() else root / xf
        X, n, delta = rebound_extra(derived, json.loads(p.read_text()))
        if n:
            _write(p, X)
        summary[p.name] = dict(rebound=n, delta=delta)
    print("R8_REFRESH OK table", A.table, "extras", json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
