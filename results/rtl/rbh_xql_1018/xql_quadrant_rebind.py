#!/usr/bin/env python3
"""RBH-XQL 2026-10-18: d4g plan (b) item 9 -- x-load per quadrant.  Derives the d4g rebinding of the x-load from the
GEN0 contract (d4f r8b netlist on the d4g plan): the stack-level xl_<S>_ctl (reads 8 W-slice banks, drives 4 SM-pair
blocks) becomes one x-load per quadrant (reads ONLY its own 8 banks vmb_<Q>0..7, drives ONLY its own 2 pairs).
Masters are unchanged (ctlx, aq13_fmt, bfqg, bdring, pegress); W quadrants keep pairs 0/1, E quadrants take the old
pairs 2/3 renamed p0/p1 behind a NEW xl_<E>_ctl + xl_<E>_aq{lo,hi}.
usage: xql_quadrant_rebind.py <gen0 contract.json[.gz]> <out.json>  (committed output gzipped)"""
import gzip, json, re, sys

QUADS = {"SW": ("SW", 0, 100), "SE": ("SW", 1, 101), "NW": ("NW", 0, 102), "NE": ("NW", 1, 103)}  # q: (stack, E?, F20)


def load(p):
    return json.load(gzip.open(p, "rt") if p.endswith(".gz") else open(p))


def main(src, out):
    c = load(src)
    inst, edges = c["instances"], c["edges"]
    res = {"schema": "opentallas.hbm_d4g.xql_quadrant_rebind.v1", "lane": "RTL-BUILD-HBM/xql", "date": "2026-10-18",
           "basis": src, "instances": {}, "removed_instances": [], "straps": [], "edges": [], "removed_edges": [],
           "host_status_slots_needed": [], "checks": {}}

    def qmap(name):
        """old instance name -> list of new quadrant instance names (shared drivers are split per quadrant)."""
        m = re.match(r"^xq_(SW|NW)_p(\d)_(\w+)$", name)
        if m:
            s, p, leaf = m.group(1), int(m.group(2)), m.group(3)
            q = s if p < 2 else ("SE" if s == "SW" else "NE")
            return [f"xq_{q}_p{p % 2}_{leaf}"]
        m = re.match(r"^xl_(SW|NW)_(ctl|aqlo|aqhi)$", name)
        if m:
            s, leaf = m.groups()
            return [f"xl_{s}_{leaf}", f"xl_{'SE' if s == 'SW' else 'NE'}_{leaf}"]
        return None

    def quad_of(newname):
        return re.match(r"^x[lq]_(SW|SE|NW|NE)_", newname).group(1)

    for q, (s, e, tgt) in QUADS.items():
        for leaf in ("ctl", "aqlo", "aqhi"):
            o = inst[f"xl_{s}_{leaf}"]
            n = {k: o[k] for k in ("master", "source", "params") if k in o}
            n["note"] = (f"d4g quadrant {q} x-load {leaf} (RBH-XQL 10-18): same master/params as GEN0 xl_{s}_{leaf}; "
                         f"serves only sm_{s}{4 * e}..{4 * e + 3} via xq_{q}_p0/p1" + ("; reads only vmb_%s0..7 rq2/rr2" % q if leaf == "ctl" else ""))
            n["ports"] = o["ports"]
            res["instances"][f"xl_{q}_{leaf}"] = n
        res["straps"].append({"inst": f"xl_{q}_ctl", "port": "tgt", "value": tgt, "lo": 0, "hi": 8,
                              "master": inst[f"xl_{s}_ctl"]["master"], "reason": f"identity: F20 target id {tgt} (x-load issuer 100 + QID, QID {list(QUADS).index(q)})"})
        for p in range(2):
            for leaf in ("bfq0", "bfq1", "bfq2", "bfq3", "bd", "eg"):
                old = f"xq_{s}_p{p + 2 * e}_{leaf}"
                o = inst[old]
                res["instances"][f"xq_{q}_p{p}_{leaf}"] = {"master": o["master"], "source": o["source"], "params": o["params"],
                                                         "renamed_from": old if e else None,
                                                         "note": f"d4g quadrant {q} pair {p} (sm_{s}{4 * e + 2 * p}/sm_{s}{4 * e + 2 * p + 1}) {leaf}; master unchanged"}
    res["removed_instances"] = [n for n in inst if re.match(r"^xq_(SW|NW)_p[23]_", n)]
    nsplit = 0
    for ed in edges:
        so, si = ed["source"], ed["sink"]
        ms, mk = qmap(so[0]), qmap(si[0])
        if ms is None and mk is None:
            continue
        res["removed_edges"].append(ed["name"])
        if ms and mk:                                  # x-load internal edge: driver follows the sink's quadrant
            nk = mk[0]; q = quad_of(nk)
            ns = [x for x in ms if quad_of(x) == q] if len(ms) == 2 else ms
            if len(ms) == 2 and len(mk) == 2:          # xl_<S>_x -> xl_<S>_y: one per quadrant
                for a, b in zip(ms, mk):
                    res["edges"].append(dict(ed, name=f"{ed['name']}__{quad_of(b)}", source=[a] + so[1:], sink=[b] + si[1:], basis="RBH-XQL quadrant split of " + ed["name"]))
                continue
            if quad_of(ns[0]) != quad_of(nk):
                raise SystemExit(f"cross-quadrant edge after split: {ns[0]} -> {nk}")
            res["edges"].append(dict(ed, name=f"{ed['name']}__q", source=[ns[0]] + so[1:], sink=[nk] + si[1:], basis="RBH-XQL quadrant rebind of " + ed["name"]))
            nsplit += 1
            continue
        if ms:                                         # x-load -> outside (vm rq2, host_status)
            for a in ms:
                q = quad_of(a); sink = list(si)
                if re.match(r"^vmb_(SW|NW)\d$", si[0]):
                    sink[0] = re.sub(r"^vmb_(SW|NW)", "vmb_" + q, si[0])
                elif si[0] == "host_status" and q in ("SE", "NE"):
                    res["host_status_slots_needed"].append({"from": [a, so[1]], "port": si[1], "like": si[2:], "target": QUADS[q][2]})
                    sink = ["host_status", si[1], None, None]
                res["edges"].append(dict(ed, name=f"{ed['name']}__{q}", source=[a] + so[1:], sink=sink, basis="RBH-XQL quadrant rebind of " + ed["name"]))
        else:                                          # outside -> x-load (host F20 broadcast, vm rr2)
            for b in mk:
                q = quad_of(b); src_ = list(so)
                if re.match(r"^vmb_(SW|NW)\d$", so[0]):
                    src_[0] = re.sub(r"^vmb_(SW|NW)", "vmb_" + q, so[0])
                res["edges"].append(dict(ed, name=f"{ed['name']}__{q}", source=src_, sink=[b] + si[1:], basis="RBH-XQL quadrant rebind of " + ed["name"]))
    # checks: R1 (no x-load edge crosses quadrants; banks only own quadrant), pairs per quadrant
    bad = []
    for ed in res["edges"]:
        qs = {quad_of(x) for x in (ed["source"][0], ed["sink"][0]) if re.match(r"^x[lq]_", x)}
        qb = {re.match(r"^vmb_(\w\w)\d$", x).group(1) for x in (ed["source"][0], ed["sink"][0]) if re.match(r"^vmb_", x)}
        if len(qs | qb) > 1:
            bad.append(ed["name"])
    res["checks"] = {"R1_cross_quadrant_edges": bad, "edges_new": len(res["edges"]), "edges_removed": len(res["removed_edges"]),
                     "instances_new_or_renamed": len(res["instances"]), "instances_removed": len(res["removed_instances"]),
                     "bank_edges_per_quadrant": {q: sum(1 for ed in res["edges"] if f"vmb_{q}" in (ed["source"][0][:6], ed["sink"][0][:6])) for q in QUADS}}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res["checks"]))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
