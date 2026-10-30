#!/usr/bin/env python3
"""HBM-BIND-7: bit-level structural proof of the spliced hub collectives against the Yosys reference.

REF = Codex's exact outer-wrapper probe elaboration of the actual sources (codex-hbm-bind-1355 probe_body/asbuilt.json,
top coll_exact_probe, hb_coll_NE / hb_coll_NW with the die's parameters).  DUT = the spliced die netlist the strict bind
consumes.  Both are flattened with tools/die_plan/bind_elab.flatten (parent interfaces retained).  For every terminal
(cell path, port, bit) of every flat cell under hb_coll_NE / hb_coll_NW the net class must be equal:
  constant          the same literal;
  parent-port net   the same set of parent port bits (port, bit) of that hub instance;
  internal net      the same set of terminals inside the hub (path, port, bit).
Cells (paths, modules, kinds, parameters) must be identical and every terminal present in both.  The composition of
the plan parts (coll_parent_cutmap.py) is then an exact partition of these cells (checked from the compose spec) and
bind_compose proves terminal equality of each composed core at bind time.
--mutant swap_reduce_in: swap u_body.u_reduce in_flit bits 0/1 of the NE body in the DUT before flattening (must FAIL).
usage: prove_coll.py REF.json DUT.json COMPOSE.json REPORT.json --tools TOOLS_DIE_PLAN [--mutant swap_reduce_in]"""
import argparse, collections, json, sys
from pathlib import Path

HUBS = ("hb_coll_NE", "hb_coll_NW")


def classes(F, hub):
    cells = [c for c in F.cells if c.path.startswith(hub + ".")]
    pp = collections.defaultdict(set)
    for pn, v in F.instances[hub]["ports"].items():
        for i, b in enumerate(v["bits"]):
            if isinstance(b, int):
                pp[b].add((pn, i))
    terms = collections.defaultdict(set)
    for c in cells:
        for p, bs in c.ports.items():
            for i, b in enumerate(bs):
                if isinstance(b, int):
                    terms[b].add((c.path, p, i))
    out, meta = {}, {}
    for c in cells:
        meta[c.path] = (c.module, c.kind, json.dumps(getattr(c, "params", {}), sort_keys=True, default=str))
        for p, bs in c.ports.items():
            for i, b in enumerate(bs):
                if isinstance(b, str):
                    k = ("C", b)
                elif b in pp:
                    k = ("P", tuple(sorted(pp[b])))
                else:
                    k = ("N", tuple(sorted(terms[b])))
                out[(c.path, p, i)] = k
    return out, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("dut"); ap.add_argument("compose"); ap.add_argument("report")
    ap.add_argument("--tools", required=True)
    ap.add_argument("--mutant", choices=("swap_reduce_in",))
    a = ap.parse_args()
    sys.path.insert(0, a.tools)
    import bind_elab as E
    R = json.loads(Path(a.ref).read_text())
    D = json.loads(Path(a.dut).read_text())
    if a.mutant == "swap_reduce_in":
        t = D["modules"]["hbm_current_native_top"]["cells"]["hb_coll_NE"]["type"]
        bt = next(c["type"] for c in D["modules"][t]["cells"].values())
        cc = D["modules"][bt]["cells"]["u_reduce"]["connections"]["in_flit"]
        cc[0], cc[1] = cc[1], cc[0]
    FR = E.flatten(R, "coll_exact_probe", (), retain_hierarchy_ports=list(HUBS))
    FD = E.flatten(D, "hbm_current_native_top", (), retain_hierarchy_ports=list(HUBS))
    spec = json.loads(Path(a.compose).read_text())
    rep = dict(schema="hbm.bind7.coll_proof.v1", ref=a.ref, dut=a.dut, mutant=a.mutant, hubs={})
    ok = True
    for hub in HUBS:
        cr, mr = classes(FR, hub)
        cd, md = classes(FD, hub)
        mism = [k for k in cr if cd.get(k) != cr[k]]
        extra = [k for k in cd if k not in cr]
        cells_eq = mr == md
        params_eq = FR.instances[hub]["params"] == FD.instances[hub]["params"]
        mem = sorted(m for c in spec["cores"] if c["inst"].startswith(hub + ".__cut_") for m in c["members"])
        partition = mem == sorted(md) and len(set(mem)) == len(mem)
        kinds = collections.Counter(v[0] for v in cr.values())
        h = dict(cells=len(md), terminals=len(cr), classes=dict(kinds), mismatches=len(mism), extra_terminals=len(extra),
                 cells_identical=cells_eq, parent_params_equal=params_eq, parent_params=FD.instances[hub]["params"],
                 parts_exact_partition=partition, parts=len([c for c in spec["cores"] if c["inst"].startswith(hub + ".__cut_")]),
                 first_mismatches=[dict(terminal=list(k), ref=str(cr[k])[:200], dut=str(cd.get(k))[:200]) for k in mism[:5]])
        h["verdict"] = "PASS" if not mism and not extra and cells_eq and params_eq and partition else "FAIL"
        ok &= h["verdict"] == "PASS"
        rep["hubs"][hub] = h
    rep["verdict"] = "PASS" if ok else "FAIL"
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: {x: y for x, y in v.items() if x not in ("first_mismatches", "parent_params")} for k, v in rep["hubs"].items()}), rep["verdict"])


if __name__ == "__main__":
    main()
