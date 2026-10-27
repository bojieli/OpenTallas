#!/usr/bin/env python3
"""HBM-CORE-LAT-R3 (hfd_ep_static): core_infra_htree plan (OUT + OUT.json) + phys_gate prediction -> frozen plan record
for tools/die_plan/core_plan_to_infra.py (nodes_xy, frozen_masters, leaf_sinks, entry, TT/FF leaf stats).

Plan geometry only: nodes/masters/sink membership are the htree plan's (12.8 b/d1); the TT/FF numbers are the
phys_gate (uf_phys3, OT_PHYS_FIT) per-leaf predictions, never a measurement.  Macro clock pins become same-stage
sibling leaves of their matched leaf (core_infra.named_tree_report convention: master = leaf master, parent = leaf
parent, load_class macro).  usage: htree_record.py PLAN_TCL PLAN_JSON GEO PRED_JSON OUT_JSON [--name NAME]
"""
import json
import re
import sys
from pathlib import Path


def tcl_items(body):
    """split a Tcl list body into top-level items (brace-aware)."""
    out, depth, cur = [], 0, ""
    for ch in body:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(cur); cur = ""
                continue
        if depth >= 1:
            cur += ch
        elif not ch.isspace():
            cur += ch
        elif cur:
            out.append(cur); cur = ""
    if cur.strip():
        out.append(cur)
    return [o for o in out if o.strip()]


def block(txt, var):
    m = re.search(r"^set %s \{\n(.*?)^\}" % re.escape(var), txt, re.S | re.M)
    return m.group(1) if m else ""


def main():
    spec, pj, geo, pred, out = sys.argv[1:6]
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else Path(spec).stem
    P = json.loads(Path(pj).read_text())
    txt = Path(spec).read_text()
    # leaves with frozen named membership from the plan Tcl
    leaf_sinks = {}
    for ln in block(txt, "ot_ms_leaves").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        it = tcl_items(ln[1:-1])          # name par {x y} {{inst} {pin}}... cell
        nm, sinks = it[0], tcl_items(it[3])
        leaf_sinks[nm] = [tcl_items(s)[0] + "/" + tcl_items(s)[1] for s in sinks]
    macpin = {}
    for ln in open(geo):
        f = ln.split()
        if f and f[0] == "MACRO":
            macpin[f[1]] = f[7]
    nodes, masters = [], {}
    for nm, par, xy, master, kind in P["nodes"]:
        k = "entry" if not par else kind
        nodes.append([nm, par or None, [round(xy[0], 4), round(xy[1], 4)], master, k])
        masters[nm] = master
    leafpar = {n[0]: (n[1], n[3]) for n in nodes}
    macro_leaves = []
    for k, (inst, leaf, xy) in enumerate(P.get("macros", [])):
        par, master = leafpar[leaf]
        nm = f"macro{k}"
        nodes.append([nm, par, [round(xy[0], 4), round(xy[1], 4)], master, "leaf"])
        masters[nm] = master
        leaf_sinks[nm] = [inst + "/" + macpin[inst]]
        macro_leaves.append(nm)
    Q = json.loads(Path(pred).read_text())
    rec = dict(name=name, model="core_infra_htree plan + phys_gate %s (PLAN MODEL, UNCHECKED)" % Q["params"]["fit"],
               entry=list(P["entry"]), nodes_xy=nodes, frozen_masters=masters, leaf_sinks=leaf_sinks,
               macro_leaves=macro_leaves)
    for C, key in (("TT", "TT_rise"), ("FF", "FF_early")):
        s = Q[key]
        rec[C] = dict(sink_min=s["min"], sink_max=s["max"], window=s["window"], mean=s["mean"],
                      basis=key, htree_internal_model=P["pred"].get(C))
    Path(out).write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict(nodes=len(nodes), leaves=len(leaf_sinks), sinks=sum(map(len, leaf_sinks.values())),
                          macro_leaves=len(macro_leaves), TT=rec["TT"]["mean"], FF=rec["FF"]["mean"])))


if __name__ == "__main__":
    main()
