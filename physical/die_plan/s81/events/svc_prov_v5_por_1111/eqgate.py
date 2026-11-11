#!/usr/bin/env python3
"""S81-SVCRS-3 11-10 EQ gate for composing the svc provider event v5 onto the S81 plan of record.

The v5 event (svc_prov_event_1109.py --lo-pack b --rdpipe, then svc_prov_step3_ft_1109.py) was made on main's plan
d67f6ffb (lineage L1) and committed as events/plan_h2_2249_svcprov_v5_517fbf9ecffb8b8f.json.gz.  The same two tools,
unchanged, are re-applied to the plan of record b05c29bb (lineage L2).  The gate proves the composed event is the SAME
event: the patch (base -> event plan) is identical on both lineages, key by key.

  patch(A, B) = every leaf path where A and B differ: numeric leaves -> B - A (rounded 1e-6), others -> B
  (list elements of partitions / ports keyed by their 'name' / 'id' when present, else by index)

PASS = (1) patch(POR, NEW) == patch(V5BASE, V5OUT), excluding only partition_types.*.port_buf_at_pin (PBP-SVCRS-1110,
present in the POR, absent in L1) and the top-level 'note' text; (2) for every type and top key the patch touches, the
base values agree on both lineages wherever the patch reads them (so an equal patch means an equal result).

    eqgate.py POR NEW V5BASE V5OUT OUT.json
"""
import json, sys


def key_of(x, i):
    if isinstance(x, dict):
        for k in ("name", "id", "inst"):
            if isinstance(x.get(k), str):
                return "%s=%s" % (k, x[k])
    return "#%d" % i


def flat(v, p, out):
    if isinstance(v, dict):
        if not v:
            out[p] = {}
        for k, x in v.items():
            flat(x, p + "/" + k, out)
    elif isinstance(v, list):
        keys = [key_of(x, i) for i, x in enumerate(v)]
        if len(set(keys)) != len(keys):
            keys = ["#%d" % i for i in range(len(v))]
        out[p + "/len"] = len(v)
        for k, x in zip(keys, v):
            flat(x, p + "/" + k, out)
    else:
        out[p] = v


def patch(a, b):
    fa, fb = {}, {}
    flat(a, "", fa); flat(b, "", fb)
    d = {}
    for p in set(fa) | set(fb):
        x, y = fa.get(p, "<absent>"), fb.get(p, "<absent>")
        if x == y:
            continue
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
            d[p] = ("delta", round(y - x, 6))
        else:
            d[p] = ("set", y)
    return d, fa


def skip(p):
    return p.startswith("/note") or "/port_buf_at_pin" in p


POR, NEW, V5B, V5O = (json.load(open(f)) for f in sys.argv[1:5])
res = dict(schema="s81svcrs3.svcprov_v5_por_eqgate.v1", inputs=sys.argv[1:5], sections={})
ok = True
sections = sorted(set(POR) | set(NEW) | set(V5B) | set(V5O))
for s in sections:
    if s == "partition_types":
        subs = sorted(set(POR[s]) | set(NEW[s]) | set(V5B[s]) | set(V5O[s]))
        items = [("partition_types/" + t, POR[s].get(t), NEW[s].get(t), V5B[s].get(t), V5O[s].get(t)) for t in subs]
    else:
        items = [(s, POR.get(s), NEW.get(s), V5B.get(s), V5O.get(s))]
    for name, a, b, c, d in items:
        p2, fa = patch(a, b)
        p1, fc = patch(c, d)
        p2 = {k: v for k, v in p2.items() if not skip("/" + name + k)}
        p1 = {k: v for k, v in p1.items() if not skip("/" + name + k)}
        if not p1 and not p2:
            continue
        same_patch = p1 == p2
        # numeric deltas: the base values must agree too (equal delta on different bases would be a different result)
        base_diff = [k for k, (op, _) in p2.items() if op == "delta" and fa.get(k) != fc.get(k)]
        row = dict(paths=len(p2), same_patch=same_patch, base_value_mismatch=len(base_diff))
        if not same_patch:
            only1 = sorted(set(p1) - set(p2)); only2 = sorted(set(p2) - set(p1))
            vald = sorted(k for k in set(p1) & set(p2) if p1[k] != p2[k])
            row.update(only_v5=only1[:20], n_only_v5=len(only1), only_por=only2[:20], n_only_por=len(only2),
                       value_diff=[[k, p1[k], p2[k]] for k in vald[:20]], n_value_diff=len(vald))
        if base_diff:
            row["base_value_mismatch_paths"] = base_diff[:20]
        ok = ok and same_patch and not base_diff
        res["sections"][name] = row
res["verdict"] = "PASS" if ok else "FAIL"
json.dump(res, open(sys.argv[5], "w"), indent=1)
print(res["verdict"], len(res["sections"]), "sections touched")
for k, v in res["sections"].items():
    if not (v["same_patch"] and not v["base_value_mismatch"]):
        print(" FAIL", k, {x: v[x] for x in v if x.startswith("n_") or x == "base_value_mismatch"})
