"""LANDING-REMAP (HEAD-REMAP-1 11-14): old -> new rewrite of every generated-name reference a plan event renumbers.

A plan event that moves hard cores / taps re-solves the generated structures and renumbers them, while the plan names
generated objects literally:
  * reset relays 'rst_rl_<k>'  (clock.landing_reader_start / landing_writer_start stages raw_reset, landing_local_resets
    raw)  -> "reader START raw reset rst_rl_60 has no registered wavefront driver" after the hd_mesh SRAM pair move;
  * density taps 'clk_t<i>' (numbered in (y, x) order of the solved tap table) in clock.landing_contract.pins[]
    source_clock_port -> "forwarded source clk_t218" invalid after the hd_lep0N tx-row / tap move.
Identity, not index:
  * relay  = (depth, site): reset_anchor.record on the OLD tree, reset_anchor.resolve on the NEW tree (nearest
    non-ported relay of the same depth within tol_um, fail closed).
  * tap    = (sink group, site): the registers the tap serves (taps.assign split, sink coordinates), the old tap whose
    group overlaps most with a new tap's group is its successor (injective, greedy by overlap); no overlap -> nearest
    new tap by Manhattan distance within tap_radius_um; none -> fail closed.
Only density-mode types carry generated tap names (explicit taps are named by the plan).  A type whose references
still resolve to the same relay / tap is left byte-identical.  A reference that is not a relay of the OLD tree (e.g. a
landing_raw_branches stage on the landing-side relay cland_reset_<bus>) is never rewritten; the receipt lists it under
resets[].kept.  Output: the new plan with every reference rewritten
plus a receipt (old -> new, moved um, overlap).

  python3 landing_remap.py OLD_PLAN NEW_PLAN OUT [--types T1,T2] [--root DIR] [--receipt FILE] [--keep-anchor]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_anchor as RA  # noqa: E402

TAP = re.compile(r"^clk_t\d+$")
SKIP_KEYS = ("taps",)           # explicit tap tables are plan-named, never generated


class RemapError(ValueError):
    pass


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def tap_refs(t):
    """[(container, key)] of every generated density tap name 'clk_t<i>' the type's clock section references
    (landing_contract source_clock_port etc.); clock.taps[] rows are definitions, not references."""
    out = []

    def walk(o):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if isinstance(k, str) and k in SKIP_KEYS:
                continue
            if isinstance(v, str) and TAP.match(v):
                out.append((o, k))
            else:
                walk(v)
    walk((t.get("clock") or {}))
    return out


def match_taps(old, new, tol_um, need=None):
    """old / new: {name: (xy, frozenset(sink keys))}.  -> {old name: (new name, moved_um, overlap)} for every old
    name (or every name in `need`: unreferenced taps may vanish); injective; same-name identical group = identity.  Raises RemapError (fail closed) when a name has no
    successor within tol_um."""
    cand = []
    for on, (oxy, og) in old.items():
        for nn, (nxy, ng) in new.items():
            ov = len(og & ng)
            cand.append((-ov, _d(oxy, nxy), on, nn, ov))
    cand.sort()
    out, used = {}, set()
    for _, dist, on, nn, ov in cand:
        if on in out or nn in used or ov <= 0:
            continue
        out[on] = (nn, dist, ov)
        used.add(nn)
    bad = []
    for on in sorted(old):
        if on in out or (need is not None and on not in need):
            continue
        free = [(_d(old[on][0], v[0]), nn) for nn, v in new.items() if nn not in used]
        if not free or min(free)[0] > tol_um:
            bad.append(f"{on} @ {old[on][0]}: " + (f"nearest free tap {min(free)[1]} is {min(free)[0]:.1f} um > tol {tol_um:g}"
                                                    if free else "no free tap"))
            continue
        dist, nn = min(free)
        out[on] = (nn, dist, 0)
        used.add(nn)
    if bad:
        raise RemapError(f"{len(bad)} tap name(s) have no successor: " + "; ".join(bad[:5]))
    return out


def remap_type_taps(tn, t_new, mapping):
    """rewrite the tap references of t_new through mapping (old name -> (new, ..)); -> receipt rows"""
    rows = []
    refs = tap_refs(t_new)
    missing = sorted({c[k] for c, k in refs} - set(mapping))
    if missing:
        raise RemapError(f"{tn}: tap reference(s) {missing[:8]} are not in the old plan's tap table")
    for n in sorted({c[k] for c, k in refs}):
        nn, dist, ov = mapping[n]
        if nn != n:
            rows.append(dict(name=n, to=nn, moved_um=round(dist, 3), shared_sinks=ov))
    for c, k in refs:
        c[k] = mapping[c[k]][0]
    return rows


def tap_groups(P, tn):
    """{tap name: (xy, frozenset of (x, y) sink keys)} of the density tap table of type tn under plan P"""
    import taps
    tbl = taps.density_taps(P, tn)
    ck = P.types[tn].get("clock", {})
    cap = int(ck.get("tap_max_sinks", 1500))
    radius = float(ck.get("tap_radius_um", 200.0))
    pts = taps.sink_sites(P, tn, True)
    _, _, asg = taps.assign([(None, x, y) for _, x, y, _, _ in tbl], pts, cap, radius, max_distance_um=radius)
    g = [set() for _ in tbl]
    for p, j in zip(pts, asg):
        g[j].add((round(p[0], 2), round(p[1], 2)))
    return {n: ((x, y), frozenset(g[i])) for i, (n, x, y, _, _) in enumerate(tbl)}


def adopt_by_key(old_t, new_t):
    """names the NEW plan inherited from its compose (stale against OLD's solved tree: OLD's prepare fix-ups such as
    HEAD-99 remap19.py renamed them) are taken from OLD by stable KEY: export row = port, landing pin = name, START
    stage = (section, bus, index), local reset = name.  -> list of [key, was, now]."""
    out = []
    oe = {e.get("port"): e for e in old_t.get("reset_start_raw_exports") or []}
    for e in new_t.get("reset_start_raw_exports") or []:
        o = oe.get(e.get("port"))
        for f in ("instance", "net"):
            if o is not None and f in o and e.get(f) != o[f]:
                out.append([f"export {e.get('port')}.{f}", e.get(f), o[f]])
                e[f] = o[f]
    ock, nck = old_t.get("clock") or {}, new_t.get("clock") or {}
    op = {p.get("name"): p for p in (ock.get("landing_contract") or {}).get("pins") or []}
    for p in (nck.get("landing_contract") or {}).get("pins") or []:
        o = op.get(p.get("name"))
        for f in ("source_instance", "source_copy_from_net"):
            if o is not None and f in o and p.get(f) != o[f]:
                out.append([f"pin {p.get('name')}.{f}", p.get(f), o[f]])
                p[f] = o[f]
    for sec in ("landing_reader_start", "landing_writer_start"):
        ob = (ock.get(sec) or {}).get("branches") or {}
        for bus, br in ((nck.get(sec) or {}).get("branches") or {}).items():
            for i, st in enumerate(br.get("stages") or []):
                os_ = ((ob.get(bus) or {}).get("stages") or [])
                if i < len(os_) and os_[i].get("raw_reset") and st.get("raw_reset") != os_[i]["raw_reset"]:
                    out.append([f"{sec}.{bus}.{i}", st.get("raw_reset"), os_[i]["raw_reset"]])
                    st["raw_reset"] = os_[i]["raw_reset"]
    ol = {x.get("name"): x for x in ock.get("landing_local_resets") or []}
    for x in nck.get("landing_local_resets") or []:
        o = ol.get(x.get("name"))
        if o is not None and o.get("raw") and x.get("raw") != o["raw"]:
            out.append([f"local_reset {x.get('name')}", x.get("raw"), o["raw"]])
            x["raw"] = o["raw"]
    return out


def _xy_snapshot(t):
    ck = t.get("clock") or {}
    return dict(exports={e.get("port"): list(e["xy_um"]) for e in t.get("reset_start_raw_exports") or [] if e.get("xy_um")},
                pins={p.get("name"): list(p["xy_um"]) for p in (ck.get("landing_contract") or {}).get("pins") or [] if p.get("xy_um")})


def _xy_restore(t, snap, max_um):
    """reset_resel moves an export row and its landing pin onto the re-selected relay; HEAD pins are fixed interface sites
    (face / core pins): put the recorded PIN xy back and return the rows whose relay is farther than max_um.  The export
    row xy_um is the relay site and stays at the rebuilt tree position."""
    far = []
    for e in t.get("reset_start_raw_exports") or []:
        o = snap["exports"].get(e.get("port"))
        if o is not None and e.get("xy_um"):
            d = _d(o, e["xy_um"])
            if d > max_um:
                far.append(f"{e['port']} relay {e.get('instance')} {d:.0f} um")
            # HEAD-99 11-15: the export row xy_um IS the registered raw relay site (landing_contract._typed_raw_reset_output
            # compares it with the rebuilt reset tree to 1e-6): keep the xy reset_resel wrote.  Only the landing PIN (a fixed
            # interface site) is restored below.  Restoring the row left 41 stale xy rows when the relays moved (G0 rp21z20).
    for p in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or []:
        o = snap["pins"].get(p.get("name"))
        if o is not None:
            p["xy_um"] = o
    return far


def resel_resets(old_raw, new_raw, names, plan_dir):
    """default reset step: street_rule.reset_resel (exports, pin sources, START stages, local resets by role + depth +
    nearest old site).  -> {type: record}; mutates new_raw."""
    import street_rule
    return street_rule.reset_resel(old_raw, new_raw, names, Path(plan_dir) / "die_plan.json")


def remap_plan(old_raw, new_raw, root, plan_dir, types=None, keep_anchor=False, tree_fn=None, groups_fn=None, tol_um=None,
               ported_fn=RA.ported, resets="resel", resel_fn=None, adopt=True, keep_xy=True, max_um=405.0):
    """rewrite new_raw in place.  resets: 'resel' (street_rule.reset_resel: raw exports, pin sources, START stages, local
    resets) or 'anchor' (reset_anchor record on the OLD tree + resolve on the NEW tree: START stages / local resets only).
    tree_fn(raw, tn) -> reset tree (anchor mode), groups_fn(raw, tn) -> tap groups, resel_fn(old, new, names, dir):
    injectable for tests.  -> receipt dict."""
    import schema
    plans = {}

    def plan(raw):
        if id(raw) not in plans:
            plans[id(raw)] = schema.Plan(raw, Path(plan_dir) / "die_plan.json")
        return plans[id(raw)]
    if groups_fn is None:
        groups_fn = lambda raw, tn: tap_groups(plan(raw), tn)  # noqa: E731
    rec = dict(resets=[], taps=[], skipped=[], adopted={})
    names = [tn for tn in new_raw["partition_types"] if (not types or tn in types) and tn in old_raw["partition_types"]]
    if adopt:
        for tn in names:
            ad = adopt_by_key(old_raw["partition_types"][tn], new_raw["partition_types"][tn])
            if ad:
                rec["adopted"][tn] = ad
    # taps first: the reset tree of the NEW plan reads the tap table, not the names, so the order is free; the tap
    # rewrite must precede reset_resel only in that its trees must build (landing source ports are validated at gen)
    for tn in names:
        t_new = new_raw["partition_types"][tn]
        if not tap_refs(t_new):
            continue
        ck = t_new.get("clock") or {}
        if ck.get("tap_mode") != "density":
            rec["skipped"].append(f"{tn}: tap_mode {ck.get('tap_mode')!r} (names are plan-defined)")
            continue
        m = match_taps(groups_fn(old_raw, tn), groups_fn(new_raw, tn), float(ck.get("tap_radius_um", 200.0)),
                       need={c[k] for c, k in tap_refs(t_new)})
        rows = remap_type_taps(tn, t_new, m)
        if rows:
            rec["taps"].append(dict(type=tn, remaps=rows))
    if resets == "resel":
        fn = resel_fn or resel_resets
        keep = {tn: _xy_snapshot(new_raw["partition_types"][tn]) for tn in names} if keep_xy else {}
        out = fn(old_raw, new_raw, [tn for tn in names], plan_dir)
        for tn in names:
            if keep_xy:
                far = _xy_restore(new_raw["partition_types"][tn], keep[tn], max_um)
                if far:
                    raise RemapError(f"{tn}: kept pin site is farther than {max_um:g} um from its re-selected relay: " + "; ".join(far[:5]))
        for tn, r in sorted(out.items()):
            if r.get("error"):
                raise RemapError(f"{tn}: reset_resel: {r['error']}")
            rec["resets"].append(dict(type=tn, **r))
        return rec
    if tree_fn is None:
        import reset_tree as RT
        tree_fn = lambda raw, tn: RT.for_type(plan(raw), tn)  # noqa: E731
    for tn in names:
        t_old, t_new = old_raw["partition_types"][tn], new_raw["partition_types"][tn]
        if not RA.refs(t_new):
            continue
        if [c[k] for c, k in RA.refs(t_old)] != [c[k] for c, k in RA.refs(t_new)]:
            raise RemapError(f"{tn}: OLD and NEW plans reference different relay names; remap needs the same event base")
        tol = tol_um or float(((t_old.get("clock") or {}).get(RA.KEY) or {}).get("tol_um") or 0) or None
        if tol is None:
            import reset_tree as RT
            tol = RT.relay_um(plan(old_raw))
        t_new["clock"][RA.KEY] = RA.record(t_new, tree_fn(old_raw, tn), root, tol)
        r = RA.resolve(tn, t_new, tree_fn(new_raw, tn), root, ported_fn)
        if r and r["remaps"]:
            rec["resets"].append(r)
        if not keep_anchor:
            del t_new["clock"][RA.KEY]
            if (t_old.get("clock") or {}).get(RA.KEY):
                t_new["clock"][RA.KEY] = t_old["clock"][RA.KEY]
    return rec


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("out")
    ap.add_argument("--types", default="")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--receipt")
    ap.add_argument("--keep-anchor", action="store_true")
    ap.add_argument("--move-pins", action="store_true", help="let reset_resel move export rows / landing pins onto the relay (default: rename only, pin sites kept)")
    ap.add_argument("--no-adopt", action="store_true", help="do not take stale compose names from OLD by key first")
    ap.add_argument("--resets", choices=["resel", "anchor"], default="resel")
    a = ap.parse_args(argv[1:])
    old = json.loads(Path(a.old).read_text())
    new = json.loads(Path(a.new).read_text())
    rec = remap_plan(old, new, a.root, Path(a.new).parent, set(filter(None, a.types.split(","))), a.keep_anchor,
                     resets=a.resets, adopt=not a.no_adopt, keep_xy=not a.move_pins)
    Path(a.out).write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    if a.receipt:
        Path(a.receipt).write_text(json.dumps(rec, indent=1) + "\n")
    nr = sum(len(r.get("remaps", r.get("exports", []))) + len(r.get("raw", [])) for r in rec["resets"])
    nt = sum(len(r["remaps"]) for r in rec["taps"])
    for tn, ad in rec["adopted"].items():
        print(f"  adopted by key {tn}: {len(ad)} name(s)")
    print(f"landing_remap: {nr} relay name(s), {nt} tap name(s) rewritten; skipped {len(rec['skipped'])}")
    for r in rec["resets"]:
        print(f"  reset {r['type']}: " + json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in r.items() if k != 'type'}))
        for where, name in r.get("kept") or []:
            print(f"  kept {r['type']}: {where} = {name} (not a relay of the OLD tree)")
    for r in rec["taps"]:
        for m in r["remaps"]:
            print(f"  tap {r['type']}: {m['name']} -> {m['to']} ({m['moved_um']} um, {m['shared_sinks']} shared sinks)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
