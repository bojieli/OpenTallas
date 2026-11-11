#!/usr/bin/env python3
"""PLAN-ROUTE-1 11-10: per-die core_conns sidecar for the types a die plan leaves without one (route_supply's
centroid FALLBACK), traced with core_conns_from_bind.trace from each type's bound netlist (kit gen/<type>/rtl/*_bound.sv
or the bind output rtl/<module>[__<type>].sv).  Every hard core of a traced type gets an entry: the ports
core_conns_from_bind finds wired (bus / core partners) and {} for a core with no pure-wiring partner at the bound level
(its pins land on the type's own logic = route_supply glue escape, not the all-core centroid).

  core_conns_batch.py PLAN.json PICKS.json OUT.json [--base EXISTING_core_conns.json]
PICKS = {type: bound.sv path} or {type: {"bound": bound.sv, "netlist": gate 1_2_yosys.v}}.
INTRA-TYPE HEADER PAIRS (COORD 11-11 02:5x, S81 bk_sel__t2): cores nested inside a soft header module of the type
(u_bk_sel.u_sel.g_q[k].u_q / u_c / u_g) are wired to each other INSIDE the header, which the bound module text does not
show, so the bound trace leaves them {} and G0/G0C R3-INTERNAL and route_supply saw 0 core links.  With a netlist
(the elaborated gate netlist sees through the header), every core the bound trace left empty is derived from it
(core_conns_netlist.derive: core<->core pairs, face buses, glue); a type whose bound trace wires none of its cores
while a netlist is missing is reported as nested_header_unresolved (loud, never silently {}).  With --base, the base file's types are kept unchanged and only new types are added.
Writes OUT.json ({type: {core: {port: [dest]}}}) and OUT.receipt.json (per type: source, cores traced / total)."""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_conns_from_bind as C  # noqa: E402
import core_conns_netlist as CN  # noqa: E402


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
        bound, netlist = (src.get("bound"), src.get("netlist")) if isinstance(src, dict) else (src, None)
        full = {h["inst"]: {} for h in T["hard_cores"]}
        paths = 0
        if bound:
            res = C.trace(plan, t, Path(bound).read_text(errors="replace"))
            cc = res["core_conns"][t]
            full = {h["inst"]: cc.get(h["inst"], {}) for h in T["hard_cores"]}
            paths = len(res["paths"])
        empty = [c for c, v in full.items() if not v]
        r_ = dict(src=src, cores=len(full), cores_wired_bound=len(full) - len(empty), wiring_paths=paths)
        if empty and netlist:
            nd = CN.derive(plan, t, Path(netlist), cores=empty, top=T.get("module"))
            ncc = nd["core_conns"].get(t, {})
            filled = [c for c in empty if ncc.get(c)]
            for c in filled:
                full[c] = ncc[c]
            r_.update(netlist=netlist, cores_filled_netlist=len(filled),
                      header_pairs=sum(1 for c in filled for v in ncc[c].values()
                                       for d in v if str(d).startswith("core:")))
        elif empty and len(empty) == len(full):
            r_["nested_header_unresolved"] = True
            print(f"WARNING {t}: bound trace wires none of its {len(full)} cores (cores nested in a header module?) "
                  f"and no gate netlist was given: entries stay {{}} = UNCHECKED", file=sys.stderr)
        r_["cores_wired"] = sum(1 for v in full.values() if v)
        out[t] = full
        rec[t] = r_
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    Path(a.out + ".receipt.json").write_text(json.dumps(dict(plan=a.plan, base=a.base, types=rec), indent=1) + "\n")
    n = [r for r in rec.values() if "cores" in r]
    print(f"{len(n)} types traced, {sum(r['cores_wired'] for r in n)}/{sum(r['cores'] for r in n)} cores wired; "
          f"{len(out)} types in {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
