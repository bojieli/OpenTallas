#!/usr/bin/env python3
"""CLAND-TIE-1 plan delta (FABLE-REVIEW-COL step B, owner decision 11-14): ONE clock landing contract per col family.

For every family (col_hN_rM[_pK]) the landed members share their data-landing pins; they differ only in the MONITOR pins
(which dn children exist, on which face, seam or not).  The family contract is the union:
  - dn children = union of (xy, seam, occurrence) over the landed members, max child count; one canonical position where
    one face serves every member (reach: pin move <= REACH_UM), superset positions otherwise (reported per family);
  - up pins and data-landing pins and data bands of the template (the landed member with most children);
  - tieable_children = every union child (instances tie the ones they do not use, landing_tie_children.py);
  - added_taps / sink_sites union of the family (as b3y92.py step B).
Members whose DATA landing pin set differs from the family's main set are left untouched (reported): a data landing is a
ring on a real crossing, it cannot be tied off.  Edges into the family (plan clock.landing_network.edges dst.bus,
sidecar collector.edges dst_index) are re-indexed to the union index.
    cland_col_superset.py PLAN SIDECAR OUT_PLAN OUT_SIDECAR [--fam REGEX] [--report R.json]
"""
import argparse, collections, copy, json, re, sys
REACH_UM = 405.0
UP = ("cland_up_ready", "cland_up_fault", "fclk_out_cland_up")
DN = re.compile(r"(?:cland_dn_(?:ready|fault)|fclk_in_cland_dn)_(\d+)$")


def is_mon(n):
    return n in UP or bool(DN.match(n))


def key_list(c):
    """[(key, old_index)] of a landed contract's children, key=(xy, seam, occurrence)."""
    occ = collections.Counter(); out = []
    for ch in sorted(c["collector_children"], key=lambda r: r["index"]):
        k0 = (tuple(round(v, 3) for v in ch["xy_um"]), bool(ch["seam"])); out.append(((k0[0], k0[1], occ[k0]), ch["index"])); occ[k0] += 1
    return out


def data_set(c):
    return tuple(sorted(p["name"] for p in c["pins"] if not is_mon(p["name"])))


def build(plan, side, fam_re=None, collector_only=False, keep_tree=False, keep_taps=False):
    P = plan["partition_types"]; rep = {}
    fam = collections.defaultdict(list)
    for k in P:
        if re.match(r"col_h(9|10)_", k): fam[k.split("__")[0]].append(k)
    own_up = {}                      # type -> (its own up pins, its own up edge clocks) before the template copy
    oldmap = {}                      # type -> {old index: key}
    newidx = {}                      # type -> {old index: union index}
    sidetypes = side["collector"]["types"]
    for f, ks in sorted(fam.items()):
        if fam_re and not re.search(fam_re, f): continue
        L = [k for k in ks if (P[k]["clock"].get("landing_contract") or {}).get("collector_children") is not None]
        if not L: rep[f] = "skip: none landed"; continue
        groups = collections.defaultdict(list)
        for k in L: groups[data_set(P[k]["clock"]["landing_contract"])].append(k)
        main_ds = max(groups, key=lambda d: len(groups[d]))
        main = groups[main_ds]; outliers = [k for d, v in groups.items() if d != main_ds for k in v]
        union = {}; pinsrc = {}; bandsrc = {}; clksrc = {}; nodesrc = {}
        for k in main:
            c = P[k]["clock"]["landing_contract"]; pins = {p["name"]: p for p in c["pins"]}
            oldmap[k] = {}
            for key, i in key_list(c):
                oldmap[k][i] = key; union.setdefault(key, None)
                pinsrc.setdefault(key, {n: pins[f"{n}_{i}"] for n in ("cland_dn_ready", "cland_dn_fault", "fclk_in_cland_dn") if f"{n}_{i}" in pins})
                if (c.get("bands") or {}).get(f"monitor_{i}"): bandsrc.setdefault(key, c["bands"][f"monitor_{i}"])
                ec = [e for e in P[k]["clock"].get("edge_clocks", []) if e["port"] == f"fclk_in_cland_dn_{i}"]
                if ec: clksrc.setdefault(key, ec[0])
                ch = next(r for r in c["collector_children"] if r["index"] == i); nodesrc.setdefault(key, ch["node"])
        ukeys = sorted(union, key=lambda k: (k[0], k[1], k[2])); idx = {key: i for i, key in enumerate(ukeys)}
        face = lambda k: "W" if k[0][0] < 100 else "E" if k[0][0] > 1000 else "S" if k[0][1] < 100 else "N"
        faces = sorted({face(k) for k in ukeys})
        cnt = collections.Counter(kk for k in main for kk in oldmap[k].values())
        c0 = cnt.most_common(1)[0][0] if cnt else None
        canon_ok = bool(c0) and all(abs(k[0][0] - c0[0][0]) + abs(k[0][1] - c0[0][1]) <= REACH_UM / 2 for k in ukeys)
        tmpl_k = max(main, key=lambda k: len(P[k]["clock"]["landing_contract"]["collector_children"]))
        T = P[tmpl_k]["clock"]["landing_contract"]
        upp = [p for p in T["pins"] if p["name"] in UP]
        for k in main:
            for p in P[k]["clock"]["landing_contract"]["pins"]:
                if p["name"] in UP and p["name"] not in {q["name"] for q in upp}: upp.append(p)
        datap = [p for p in T["pins"] if not is_mon(p["name"])]
        newpins = copy.deepcopy(upp) + copy.deepcopy(datap); rows = []; tie = []
        bands = {b: v for b, v in (T.get("bands") or {}).items() if not b.startswith("monitor_")}
        ecl = [e for e in P[tmpl_k]["clock"].get("edge_clocks", []) if not e["port"].startswith("fclk_in_cland_dn_")]
        for i, key in enumerate(ukeys):
            for n, p in pinsrc[key].items():
                q = copy.deepcopy(p); q["name"] = f"{n}_{i}"; newpins.append(q)
            rows.append(dict(part=None, node=nodesrc[key], xy_um=list(key[0]), seam=key[1], index=i,
                             ready=f"cland_dn_ready_{i}", fault=f"cland_dn_fault_{i}"))
            tie.append(dict(index=i, seam=key[1]))
            if key[1] and key in bandsrc:
                b = copy.deepcopy(bandsrc[key]); b["instance"] = f"u_cland_monitor_{i}"; bands[f"monitor_{i}"] = b
            if key[1] and key in clksrc:
                e = copy.deepcopy(clksrc[key]); e["port"] = f"fclk_in_cland_dn_{i}"; ecl.append(e)
        members = [k for k in (L if collector_only else ks) if k not in outliers]   # collector_only: plain tiles keep their form (no R3b)
        base = P[members[0]]["clock"].get("added_taps", []); first = int(re.sub(r"\D", "", base[0]["name"])) if base else 16
        seen = []
        for k in members:
            for t in P[k]["clock"].get("added_taps", []):
                if list(t["xy"]) not in seen: seen.append(list(t["xy"]))
        taps = [{"name": "clk_t%d" % (first + i), "xy": xy} for i, xy in enumerate(seen)]
        ss = sorted({tuple(x) for k in members for x in (P[k]["clock"].get("sink_sites_um") or [])})
        for k in main: newidx[k] = {old: idx[key] for old, key in oldmap[k].items()}
        stT = copy.deepcopy(sidetypes.get(tmpl_k))
        for k in members:
            ck = P[k]["clock"]; old_lc = ck.get("landing_contract") or {}
            own_up[k] = ([copy.deepcopy(p) for p in old_lc.get("pins", []) if p["name"] in UP],
                         [copy.deepcopy(e) for e in ck.get("edge_clocks", []) if e["port"] in UP])
            lc = json.loads(json.dumps(T).replace(tmpl_k, k))
            lc.update(pins=copy.deepcopy(newpins), collector_children=copy.deepcopy(rows), bands=copy.deepcopy(bands),
                      tieable_children=copy.deepcopy(tie), registered_monitor=True)
            if any(r["seam"] for r in rows): lc["forwarded_clock_only_inputs"] = True
            if keep_tree and "collector_tree" in (ck.get("landing_contract") or {}):
                lc["collector_tree"] = ck["landing_contract"]["collector_tree"]   # the member own tree (from compose), not the template copy
            ck["landing_contract"] = lc; ck["edge_clocks"] = copy.deepcopy(ecl); ck["added_taps"] = ck.get("added_taps", []) if keep_taps else copy.deepcopy(taps)
            if ss and not keep_taps: ck["sink_sites_um"] = [list(x) for x in ss]
            if stT is not None:
                st = json.loads(json.dumps(stT).replace(tmpl_k, k)); st["children"] = copy.deepcopy(rows); st["bands"] = copy.deepcopy(bands)
                st["mask"]["children"] = [dict(xy_um=list(k2[0]), seam=k2[1]) for k2 in ukeys]; st["mask"]["active"] = True
                st["up_parent"] = None; st["base_type"] = T.get("base_type", st.get("base_type"))
                sidetypes[k] = st
        rep[f] = dict(types=len(ks), landed=len(L), main=len(main), outliers=outliers, children_union=len(ukeys), faces=faces,
                      canonical_ok=canon_ok, pins=len(newpins), added_taps=len(taps), sink_sites=len(ss))
    # re-index the die-level edges into the rebuilt types
    part_type = {p["name"]: p["type"] for p in plan["partitions"]}
    n_pe = n_se = 0
    for e in plan["clock"]["landing_network"]["edges"]:
        m = DN.search(e["dst"]["bus"]); tn = part_type.get(e["dst"]["part"])
        if m and tn in newidx:
            old = int(m.group(1)); e["dst"]["bus"] = e["dst"]["bus"][: m.start(1)] + str(newidx[tn][old]); n_pe += 1
    for e in side["collector"]["edges"]:
        tn = part_type.get(e["dst"])
        if tn in newidx: e["dst_index"] = newidx[tn][e["dst_index"]]; n_se += 1
    rep["_edges"] = dict(plan=n_pe, sidecar=n_se)
    rep["_up_kept"] = keep_own_up(plan, own_up)
    return rep


def die_xy(part, t, xy):
    """Die point of a type-local point (partition origin + orient over the type outline)."""
    (ox, oy), (w, h), (x, y) = part["origin_um"], t["outline_um"], xy
    o = part.get("orient", "R0")
    if o in ("MY", "R180"): x = w - x
    if o in ("MX", "R180"): y = h - y
    return ox + x, oy + y


def _pin_xy(t, name):
    p = next((q for q in (t["clock"].get("landing_contract") or {}).get("pins", []) if q["name"] == name), None)
    return p.get("xy_um") if p else None


def keep_own_up(plan, own_up):
    """S81-GEOM-OPUS 11-19 (D8h plan g, fE4_p1_b0 1,045 um): the family contract copies the TEMPLATE member's up pins
    (cland_up_ready / _fault / fclk_out_cland_up) onto every member, but a member's up edge goes to its own parent, so
    the template position can sit on another face, far from it. Per member, keep its own up pins (and up edge clock)
    when the template position puts any of its up edges over the edge max hop and the own position is shorter.
    The dn side needs no rule: re-indexed edges land on the union child with the member's own key (same xy)."""
    parts = {p["name"]: p for p in plan["partitions"]}; PT = plan["partition_types"]; kept = {}
    for e in plan["clock"]["landing_network"]["edges"]:
        sp, dp = parts.get(e["src"]["part"]), parts.get(e["dst"]["part"])
        if e["src"]["bus"] not in UP or not sp or not dp or sp["type"] not in own_up or sp["type"] in kept: continue
        k = sp["type"]; st, dt = PT[k], PT[dp["type"]]
        own = {p["name"]: p.get("xy_um") for p in own_up[k][0]}
        a, b, d = _pin_xy(st, e["src"]["bus"]), own.get(e["src"]["bus"]), _pin_xy(dt, e["dst"]["bus"])
        if a is None or b is None or d is None or "origin_um" not in sp or "origin_um" not in dp: continue
        D = die_xy(dp, dt, d)
        hop = lambda xy: abs(die_xy(sp, st, xy)[0] - D[0]) + abs(die_xy(sp, st, xy)[1] - D[1])
        lim = e.get("max_hop_um", REACH_UM)
        if hop(a) > lim and hop(b) < hop(a):
            kept[k] = dict(edge=e["id"], template_hop_um=round(hop(a), 1), own_hop_um=round(hop(b), 1))
    for k in kept:
        ck = PT[k]["clock"]; lc = ck["landing_contract"]; pins, ecl = own_up[k]
        lc["pins"] = copy.deepcopy(pins) + [p for p in lc["pins"] if p["name"] not in UP]
        ck["edge_clocks"] = copy.deepcopy(ecl) + [x for x in ck.get("edge_clocks", []) if x["port"] not in UP]
    return kept


def identities(plan, rx=r"^col_", ignore=("param_set", "module", "note", "param_base_type")):
    """Distinct col type classes: everything except the module/type name, the pv param set and the child 'part' names."""
    sj = lambda x: json.dumps(x, sort_keys=True)
    cls = collections.defaultdict(list)
    for k, t in plan["partition_types"].items():
        if not re.match(rx, k): continue
        d = {a: b for a, b in t.items() if a not in ignore}
        cls[sj(d).replace(k, "@T@")].append(k)
    return cls


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("side"); ap.add_argument("oplan"); ap.add_argument("oside")
    ap.add_argument("--fam"); ap.add_argument("--report"); ap.add_argument("--collector-only", action="store_true"); ap.add_argument("--keep-tree", action="store_true"); ap.add_argument("--keep-taps", action="store_true")
    a = ap.parse_args()
    plan = json.load(open(a.plan)); side = json.load(open(a.side))
    before = len(identities(plan))
    rep = build(plan, side, a.fam, a.collector_only, a.keep_tree, a.keep_taps)
    after = identities(plan)
    geo = identities(plan, ignore=("param_set", "module", "note", "param_base_type", "hard_cores"))
    cl = collections.defaultdict(int)
    for k in after: pass
    rep["_identities"] = dict(before_all_fields=before, after_all_fields=len(after), after_ignoring_hard_core_flips=len(geo),
                              per_family={f: len({sig for sig, ks in after.items() if ks[0].split("__")[0] == f}) for f in sorted({ks[0].split("__")[0] for ks in after.values()})})
    open(a.oplan, "w").write(json.dumps(plan, indent=1)); open(a.oside, "w").write(json.dumps(side, separators=(",", ":")))
    if a.report: open(a.report, "w").write(json.dumps(rep, indent=1))
    for f, r in rep.items(): print(f, r)


if __name__ == "__main__":
    sys.exit(main())
