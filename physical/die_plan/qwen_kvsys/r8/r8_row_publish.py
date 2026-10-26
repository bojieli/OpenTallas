#!/usr/bin/env python3
"""KV-PLAN3F 10-25 (TYPE-REDUCE KV item 1, COORD-approved): R8 input prep for the KV die after r8_invariant_split.py.
The per-row R8 alignment pads of the head-group rows are replaced by a per-row latency PUBLISHED to the compiler.

Why the pads existed: r8_invariant_split.py keys an as-built bus by (sink TYPE, sink leaf name with the quadrant
blanked).  Once kv3_hg_v1 was split per row (v3.6: _r1.._r5, + _v2, _v3) every row was its own type, so an as-built
offset between two pins of one source leaf looked invariant (one row = one value) and R8 padded it: the astk ep chain
xi vs zi (+3 as built in rows 1/3/5/7, 0 in rows 2/4/6: 267 b x 3 pad flops per odd row) and ectl cfg vs kgo/epoch
(rows 4/5: 5 b x 2).  The SAME leaf RTL (qkd_astk_ep_s_e, ot ectl: one module, one parameter set in every hg row) ran
with each of those offsets as built, so by r8_invariant_split's own rule they were never functional invariants; the
static schedule (calendar per row, KV-TOK) absorbs the row's arrival depth.

(a) Replica sets (R8 (2), --replica type): with the rows merged into one type, a broadcast that reached every row at
one as-built depth (kvs_attn.acal_Q -> ep cal_exp, kvs_hroot o_kg -> ectl epoch/kgo/layer) would now be padded to the
slowest row (up to +10 cycles).  v3.9e never equalised those across rows (one type per row); the per-row depth is the
published latency.  Each replica entry's family sink partitions are split per ROW (the partition's trailing index),
so the four quadrant replicas of one row stay equalised exactly as in v3.9e.
(b) Bus groups: this pass applies the r8_invariant_split rule across the hg ROW FAMILY (--family types) with row-blind names (quadrant
tokens AND decimal index tokens blanked: g_ep_3 / ectl_EN_1 / head_EN_2_0 -> g_ep_* / ectl_*_* / head_*_*_*; a trailing
source-pin index too: kvs_hroot o_c2 -> o_c*): pins of one
source leaf whose pairwise as-built offset is not identical in every row and quadrant get their own bus_sub.  The R8
landing table then has no hg row pad; g3/row_latency_v39f.py publishes every changed member depth per row.

    r8_row_publish.py PLAN.json BUS_GROUPS_IN.json OUT.json --family kv3_hg,kv3_hg_v1,kv3_hg_v3
"""
import argparse
import json
import re
from collections import defaultdict

Q = re.compile(r"(?<![A-Za-z0-9])(EN|ES|WN|WS|\d+)(?![A-Za-z0-9])")


def norm(s):
    return Q.sub("*", s)


def npin(s):
    """row-indexed source pins (kvs_hroot o_c0 .. o_c7 -> o_c*)"""
    return re.sub(r"\d+$", "*", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("bg_in")
    ap.add_argument("out")
    ap.add_argument("--family", required=True, help="comma list of partition types forming one row family")
    a = ap.parse_args()
    fam = set(a.family.split(","))
    plan = json.load(open(a.plan))
    bg = json.load(open(a.bg_in))
    ptype = {p["name"]: p["type"] for p in plan["partitions"]}
    infam = lambda part: ptype.get(part) in fam
    # (a) replica sets: family sink partitions split per row
    rows = lambda part: part.rsplit("_", 1)[-1]
    rep_out, nrep = [], 0
    for r in bg.get("replica", []):
        fp = [x for x in r["sink_parts"] if infam(x)]
        if len({rows(x) for x in fp}) <= 1:
            rep_out.append(r)
            continue
        nrep += 1
        rest = [x for x in r["sink_parts"] if not infam(x)]
        groups = ([rest] if rest else []) + [[x for x in fp if rows(x) == k] for k in sorted({rows(x) for x in fp})]
        for ps in groups:
            q = dict(r, sink_parts=ps, bound_depths={x: v for x, v in r.get("bound_depths", {}).items() if x in ps},
                     row_split=True)
            q["equal"] = len({json.dumps(v) for v in q["bound_depths"].values()}) <= 1
            rep_out.append(q)
    bg["replica"] = rep_out
    inst = defaultdict(dict)       # (sink, sink part, src part, src leaf) -> {pin key: as-built}
    for g in bg["landing"]:
        if not infam(g["sink_part"]):
            continue
        for m in g["members"]:
            if m.get("lane") == "spine":
                continue
            leaf, _, pin = m["source"].rpartition(".")
            pk = (m["sink_port"], npin(pin), json.dumps(m["sink_bits"]))
            inst[(g["sink"], g["sink_part"], g["src_part"], leaf)][pk] = m["asbuilt_stages"]
    fb = defaultdict(list)         # family bus (row-blind) -> [instance offset maps]
    for (sink, sp, srcp, leaf), pins in inst.items():
        fb[(norm(sink), norm(srcp), norm(leaf))].append(pins)
    sub, nsplit = {}, 0
    for fk, insts in fb.items():
        keys = sorted(set().union(*[set(p) for p in insts]))
        par = {k: k for k in keys}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for i, x in enumerate(keys):
            for y in keys[i + 1:]:
                offs = {p[x] - p[y] for p in insts if x in p and y in p}
                if len(offs) == 1:
                    par[find(x)] = find(y)
        roots = sorted({find(k) for k in keys})
        if len(roots) > 1:
            nsplit += 1
        for k in keys:
            sub[(fk, k)] = roots.index(find(k))
    n = 0
    for g in bg["landing"]:
        if not infam(g["sink_part"]):
            continue
        for m in g["members"]:
            if m.get("lane") == "spine":
                continue
            leaf, _, pin = m["source"].rpartition(".")
            fk = (norm(g["sink"]), norm(g["src_part"]), norm(leaf))
            # the family split replaces the type-level one: its instance set is a superset (every row and quadrant),
            # so every pair the type-level split separated is separated here too
            new = sub[(fk, (m["sink_port"], npin(pin), json.dumps(m["sink_bits"])))]
            if new != m.get("bus_sub", 0):
                n += 1
            if new:
                m["bus_sub"] = new
            else:
                m.pop("bus_sub", None)
    bg["note"] = bg.get("note", "") + (" | KV-PLAN3F r8_row_publish: r8_invariant_split rule over the hg row family "
                                       f"{sorted(fam)} (row-blind leaf names): {nsplit} family buses split, {n} members "
                                       f"re-bused, {nrep} replica sets split per row; their per-row depth is published (lat_v39f/row_latency.json)")
    bg["row_publish"] = dict(family=sorted(fam), replica_sets_row_split=nrep, family_buses_split=nsplit,
                             members_rebused=n)
    json.dump(bg, open(a.out, "w"))
    print(f"r8_row_publish: {nrep} replica sets split per row, {nsplit} family buses split, {n} members re-bused")


if __name__ == "__main__":
    main()
