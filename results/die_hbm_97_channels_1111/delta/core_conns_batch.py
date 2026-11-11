#!/usr/bin/env python3
"""PLAN-ROUTE-1 11-10: per-die core_conns sidecar for the types a die plan leaves without one (route_supply's
centroid FALLBACK), traced with core_conns_from_bind.trace from each type's bound netlist (kit gen/<type>/rtl/*_bound.sv
or the bind output rtl/<module>[__<type>].sv).  Every hard core of a traced type gets an entry: the ports
core_conns_from_bind finds wired (bus / core partners) and {} for a core with no pure-wiring partner at the bound level
(its pins land on the type's own logic = route_supply glue escape, not the all-core centroid).

  core_conns_batch.py PLAN.json PICKS.json OUT.json [--base EXISTING_core_conns.json]
PICKS = {type: bound.sv path}.  With --base, the base file's types are kept unchanged and only new types are added.
Writes OUT.json ({type: {core: {port: [dest]}}}) and OUT.receipt.json (per type: source, cores traced / total)."""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_conns_from_bind as C  # noqa: E402


def read_json(p):
    p = Path(p)
    return json.load(gzip.open(p, "rt")) if p.suffix == ".gz" else json.loads(p.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("picks")
    ap.add_argument("out")
    ap.add_argument("--base")
    a = ap.parse_args(argv)
    plan = read_json(a.plan)
    picks = json.loads(Path(a.picks).read_text())
    out = read_json(a.base) if a.base else {}
    rec = {}
    for t, src in sorted(picks.items()):
        if t in out:
            rec[t] = dict(src="base (kept)")
            continue
        T = plan["partition_types"].get(t)
        if not T or not T.get("hard_cores"):
            rec[t] = dict(src=src, skipped="type not in plan or no hard cores")
            continue
        res = C.trace(plan, t, Path(src).read_text(errors="replace"))
        cc = res["core_conns"][t]
        full = {h["inst"]: cc.get(h["inst"], {}) for h in T["hard_cores"]}
        out[t] = full
        rec[t] = dict(src=src, cores=len(full), cores_wired=sum(1 for v in full.values() if v),
                      wiring_paths=len(res["paths"]))
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    Path(a.out + ".receipt.json").write_text(json.dumps(dict(plan=a.plan, base=a.base, types=rec), indent=1) + "\n")
    n = [r for r in rec.values() if "cores" in r]
    print(f"{len(n)} types traced, {sum(r['cores_wired'] for r in n)}/{sum(r['cores'] for r in n)} cores wired; "
          f"{len(out)} types in {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
