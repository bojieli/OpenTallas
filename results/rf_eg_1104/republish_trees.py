#!/usr/bin/env python3
"""S81 RF-EG (DIE-S81-54/EG 11-04): the event edited the 16 C types collector_tree by hand (three core resets on one tap,
n_clock_taps +2), which the solver does not produce: on main published == re-solved, on the event 172 vs 186 relays on
c1x_C__t1.  Republish the re-solved reset tree into the plan and the landed sidecar.  Text edit of those trees only.
  republish_trees.py PLAN SIDECAR            re-solve with reset_tree.for_type
  republish_trees.py PLAN SIDECAR FROM.json  take the trees and added_taps of the types that differ in FROM.json (added_tap_recentre --out)"""
import json, re, sys
sys.path.insert(0, "tools/die_plan")
import schema as S, reset_tree as RT
pf, sf, *frm = sys.argv[1:]
txt = open(pf).read(); raw = json.loads(txt); side = json.load(open(sf)); dec = json.JSONDecoder()
C = lambda o: json.dumps(o, separators=(",", ":"))
def tree_text(tree, pad):
    rows = []
    for k, v in tree.items():
        if k == "relays":
            rows.append(pad + "\"relays\": [\n" + ",\n".join(pad + " " + C(r) for r in v) + "\n" + pad + "]")
        else:
            rows.append(pad + json.dumps(k) + ": " + C(v))
    return "{\n" + ",\n".join(rows) + "\n" + pad[:-1] + "}"
def replace(tn, key, new, txt):
    i = txt.index(json.dumps(tn) + ":", txt.index("\"partition_types\""))
    j = txt.index(json.dumps(key) + ":", i); v = txt.index(":", j) + 1
    while txt[v] in " \n": v += 1
    old, e = dec.raw_decode(txt, v)
    assert key == "collector_tree" or old == raw["partition_types"][tn]["clock"][key], (tn, key)
    ls = txt.rfind("\n", 0, j) + 1; pad = txt[ls:j] + " "
    return txt[:v] + (tree_text(new, pad) if key == "collector_tree" else C(new)) + txt[e:]
if frm:
    src = json.load(open(frm[0]))["partition_types"]; names = [n for n, t in raw["partition_types"].items() if t != src[n]]
    new = {n: src[n]["clock"]["landing_contract"]["collector_tree"] for n in names}
else:
    P = S.Plan(S.load(pf), pf); src = None
    names = [n for n, t in raw["partition_types"].items() if any(c["inst"] == "u_c.u_eg.u_gg" for c in t.get("hard_cores") or [])]
    assert len(names) == 16, names
    new = {n: json.loads(json.dumps(RT.for_type(P, n))) for n in names}
for n in names:
    old = raw["partition_types"][n]["clock"]["landing_contract"]["collector_tree"]; T = new[n]
    print(n, "depth", old["depth"], T["depth"], "own", old["own_depth"], T["own_depth"], "relays", len(old["relays"]), len(T["relays"]), "nck", old["n_clock_taps"], T["n_clock_taps"], "cr", [c["tap"] for c in T["core_resets"]])
    txt = replace(n, "collector_tree", T, txt)
    raw["partition_types"][n]["clock"]["landing_contract"]["collector_tree"] = T
    side["collector"]["types"][n]["tree"] = T
    if src:
        A = src[n]["clock"]["added_taps"]; txt = replace(n, "added_taps", A, txt); raw["partition_types"][n]["clock"]["added_taps"] = A
assert json.loads(txt) == raw, "text edit differs from dict delta"
open(pf, "w").write(txt); open(sf, "w").write(C(side)); print("republish_trees OK", len(names), len(txt))
