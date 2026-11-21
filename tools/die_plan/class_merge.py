#!/usr/bin/env python3
"""UNIFY-TOOLS (FABLE-SUPERSET-0415 section 10, U1/U4/U6/U7): merge a class of partition types into ONE type.

Every instance of a member type is re-typed to the representative, so bind emits one bound module for the class and one
kit / one synthesis serves every instance (U7).  The class row is the representative's whole row (floorplan, taps, reset
tree, reader / writer start, bands: U2/U4/U6).  What may differ between members, and how it is made per instance:

  - collector (monitor) children (U1): the representative must carry every child site (xy, seam, occurrence) any member
    uses; all of them become clock.landing_contract.tieable_children, seam children get a strap_cland_use_<k> pin
    (landing_tie_children.with_use_pins).  An instance ties the children it does not use (ready 1, fault 0, clock 0)
    and its use strap is derived from its real landing edges (landing_tie_children.instance_use).  Die landing edges
    (plan clock.landing_network.edges dst.bus, sidecar collector.edges dst_index) are re-indexed by child site.
  - reset outs (U4): the representative's outs; an instance leaves the outs it does not drive open.
  - pad strap (U3): r8_strap_pad_max = the class maximum (the pad is a strap tied at the parent, OWNER 10-25 B).
  - landing role origin / relay: must be equal, or with --role-strap the class row takes every origin / relay start
    pin a member has, the count-strap union, strap_ca_relay and landing_role_strap (clock_landings ROLE-STRAP).
  - OUT kit stations (UNIFY-TOOLS-R3): a moved instance now carries the representative's OUT-bus kit stations
    (native_istations.kit_source_depth: internal_stations regs + declared core cycles).  Where that is deeper than the
    member's own chain on a lane's source bus, the lane is priced for it: lane fixed_cycles and its latency row
    fixed / cycles / natural all + delta (+cycles, OWNER pre-approved), so the bind's kit source pricing (fixed_cycles
    >= depth) still cuts the whole chain from the receiver pad and the receiver pad is unchanged.  Without it the lane
    is delivered late by the whole chain (LANE_ASBUILT UNPRICED_KIT_STATIONS).  Report rows: kit_priced.
    --reprice-from PRE_PLAN applies only this step to an already merged PLAN (instance types taken from PRE_PLAN).

  - feed-through superset (--ft-superset, UNIFY-TOOLS-R3): the class row carries the UNION of the members' ft slots
    and becomes a superset type (partition_types[].superset; FABLE-SUPERSET-0415 U5).  Slot names are STABLE: every
    slot keeps its own name when the representative owns it or no other pin set in the class uses it; a member slot
    whose name another pin set also uses becomes <name>_c<sha1(pins)[:6]> (stable: a function of its pins only).
    Slots with the same pins (faces, width, windows, layers, order, turnaround) are one physical slot: they collapse
    to the representative's slot, else to the smallest member name.  Only renamed / collapsed slots' ports and
    per-slot landing pins (fclk_in_<slot>_i, cland_fstart_in_<slot>_i, fclk_out_<slot>_o, cland_fstart_out_<slot>_o)
    and their landing edges are re-pointed; the class row gains the landing pins of its added slots.  Copies of one
    pin set with different station counts take the deepest copy; the lanes through a shallower copy get +delta in
    their latency rows (ft_stations_raised; +cycles pre-approved; re-derive R8 and rebind after).  Every instance names the class slots it does not bind (neither
    end used by a port) in partitions[].spare_ends.  Report: ft_superset {added, collapsed, spare, overlaps}, where
    overlaps lists class slot ends on one face whose windows and layers intersect (class_window_solve resolves them).

Refused (exit 2, nothing written): a member child site the representative lacks, a different outline or bus / ft pin
table (ft only without --ft-superset), a member with data landing pins the representative lacks.  Per-type die tables keyed by a member type name
(clock.tap_window / tap_offset, reset.in_sites, sidecar collector.types) are dropped; the representative's stay.

    class_merge.py PLAN SIDECAR OUT_PLAN OUT_SIDECAR --rep TYPE (--members T1,T2,.. | --stem STEM) [--report R.json]
    class_merge.py PLAN SIDECAR OUT_PLAN OUT_SIDECAR --reprice-from PRE_PLAN [--report R.json]
"""
import argparse, collections, copy, hashlib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_tie_children as LTC  # noqa: E402
import native_istations as NI  # noqa: E402

DN = re.compile(r"^(cland_dn_ready|cland_dn_fault|fclk_in_cland_dn)_(\d+)$")
UP = ("cland_up_ready", "cland_up_fault", "fclk_out_cland_up")
# type-row fields that are the class row (representative) by definition; a member's own value is replaced
CLASS_ROW = {"clock", "reset", "hard_cores", "internal_stations", "cells", "relay_sites", "note", "landing_base_type",
             "contents", "count_straps", "r8_strap_pad_max", "module", "ft_track_frac"}
# fields that must be equal: a difference means the member is not a copy of the class row
MUST_EQUAL = ("outline_um", "buses", "ft_slots")


class MergeError(Exception):
    pass


def _lc(t):
    return ((t.get("clock") or {}).get("landing_contract")) or {}


def child_keys(lc):
    """{old index: (xy, seam, occurrence)} of a landing contract's collector children."""
    occ = collections.Counter(); out = {}
    for ch in sorted(lc.get("collector_children") or [], key=lambda r: int(r["index"])):
        k0 = (tuple(round(float(v), 3) for v in ch["xy_um"]), bool(ch["seam"]))
        out[int(ch["index"])] = (k0[0], k0[1], occ[k0]); occ[k0] += 1
    return out


def data_landing_pins(lc):
    return {p["name"] for p in lc.get("pins", []) if p["name"] not in UP and not DN.match(p["name"])
            and not p["name"].startswith(LTC.MONITOR_USE_PREFIX)}


def landing_role(sidecar, part):
    """Count-aligned origin / relay role of a partition (None when it is not a count-aligned part)."""
    ca = (sidecar.get("count_aligned") or {}).get("parts") or {}
    row = ca.get(part)
    if not isinstance(row, dict):
        return None
    return row.get("role")


def free_site_on_line(pins, pin, outline, tries=16, clear_um=1.0):
    """Nearest free site for `pin` on its own layer: moved across its routing direction by whole track pairs (a V layer
    moves in x, an H layer in y; die_plan.schema layer pitch), so it stays on a track; a site is free when no same-layer
    landing pin is within clear_um.  None when no free site lies within `tries` steps inside the outline."""
    import schema as S
    lay = next((L for L in S.ASAP7_LAYERS if L["name"] == pin.get("layer")), None)
    if lay is None:
        return None
    step = 2 * lay["pitch_um"]
    x0, y0 = (float(v) for v in pin["xy_um"])
    same = [tuple(float(v) for v in q["xy_um"]) for q in pins if q.get("layer") == pin.get("layer") and "xy_um" in q]
    for k in range(1, tries + 1):
        for sgn in (1, -1):
            d = sgn * k * step
            c = (x0 + d, y0) if lay["dir"] == "V" else (x0, y0 + d)
            if not all(0 <= v <= lim for v, lim in zip(c, outline)):
                continue
            if all(abs(c[0] - a) + abs(c[1] - b) >= clear_um for a, b in same):
                return [round(c[0], 6), round(c[1], 6)]
    return None


def role_pins_union(P, rep, members, rep_out):
    """ROLE-STRAP class row: the representative takes every origin / relay start pin a member has (same name, site and
    layer as on that member), the union of the count straps (max width) plus strap_ca_relay, and landing_role_strap."""
    R = P[rep]; rlc = _lc(R)
    have = {p["name"]: p for p in rlc.get("pins", [])}
    sites = {(p["layer"], tuple(round(float(v), 3) for v in p["xy_um"])): p["name"] for p in rlc.get("pins", [])
             if "xy_um" in p and "layer" in p}
    added, src_site = [], {}      # src_site: the member site of a pin the class row moved
    for m in members:
        for pin in _lc(P[m]).get("pins", []):
            n = pin["name"]
            if n not in ROLE_PINS:
                continue
            if n in have:
                if (have[n].get("layer"), src_site.get(n, have[n].get("xy_um"))) != (pin.get("layer"), pin.get("xy_um")):
                    rep_out["refused"].append(f"{m}: role pin {n} at another site than the class row's")
                continue
            key = (pin.get("layer"), tuple(round(float(v), 3) for v in pin.get("xy_um", [])))
            q = copy.deepcopy(pin)
            if key in sites:
                # the relay rx of one copy sits where the origin tx of another copy is (the two ends of one seam
                # edge): the class row takes the next free site on the same pin line (the pitch of that line)
                xy = free_site_on_line(rlc.get("pins", []), pin, R["outline_um"])
                if xy is None:
                    rep_out["refused"].append(f"{m}: role pin {n} site is {sites[key]} on the class row, no free site")
                    continue
                rep_out.setdefault("role_pins_moved", {})[n] = [pin["xy_um"], xy]
                src_site[n] = pin["xy_um"]
                q["xy_um"] = xy; key = (pin.get("layer"), tuple(round(float(v), 3) for v in xy))
            rlc.setdefault("pins", []).append(q); have[n] = q; sites[key] = n; added.append(n)
    widths = {}
    for t in [rep] + members:
        for c in P[t].get("count_straps", []):
            widths[c["name"]] = max(widths.get(c["name"], 0), int(c["width"]))
    widths["strap_ca_relay"] = 1
    R["count_straps"] = [dict(name=n, width=w) for n, w in sorted(widths.items())]
    R["landing_role_strap"] = True
    rep_out["role_strap"] = dict(pins_added=sorted(added), count_straps=widths)


def names_used(x, names):
    """Member type names used as a dict key or a whole string value (free text such as notes does not count)."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in names:
                yield k
            yield from names_used(v, names)
    elif isinstance(x, list):
        for v in x:
            yield from names_used(v, names)
    elif isinstance(x, str) and x in names:
        yield x


ROLE_PINS = ("cland_rstart_in", "cland_rstart_out", "cland_tstart_in", "cland_tstart_out")


def price_out_stations(plan, before):
    """price the representative's OUT kit stations on lanes leaving re-typed instances.  before: {part: pre-merge type
    row} of the moved instances.  A lane is priced only where the bind priced the member chain (fixed_cycles >= member
    depth; otherwise the lane never had kit source pricing), the class chain is deeper, and the lane is predicted late
    with the class chain (late_by_kit: a receiver pad that still absorbs the change leaves the lane as it is).
    -> [{lane, part, bus, member, rep, add, late}]"""
    ports = {x["id"]: x for x in plan.get("ports", [])}
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}
    tab = (plan.get("latency") or {}).get("lanes", {})
    out = []
    for ln in plan.get("lanes", []):
        if ln.get("spine") or not ln.get("ports") or ln["ports"][0] not in ports:
            continue
        a, z = ports[ln["ports"][0]]["src"], ports[ln["ports"][-1]]["dst"]
        old = before.get(a["part"])
        if old is None:
            continue
        new = plan["partition_types"][ptype[a["part"]]]
        if new.get("realize_internal_stations") or old.get("realize_internal_stations"):
            continue
        n_old, n_new = NI.kit_source_depth(old, a["bus"]), NI.kit_source_depth(new, a["bus"])
        fx = int(ln.get("fixed_cycles", 0) or 0)
        if n_new <= n_old or fx < n_old:
            continue
        add = n_new - n_old
        row = tab.get(ln["id"])
        if row is None:
            raise MergeError(f"lane {ln['id']} leaves re-typed {a['part']} with +{add} kit stations but has no latency row")
        if int(row.get("fixed", 0) or 0) != fx:
            raise MergeError(f"lane {ln['id']}: latency row fixed {row.get('fixed')} != lane fixed_cycles {fx}")
        m = dest_depth(plan["partition_types"].get(ptype.get(z["part"]), {}), z["bus"])
        late = late_by_kit(row, fx, n_new, m)
        if late <= 0:
            continue
        ln["fixed_cycles"] = fx + add
        for k in ("fixed", "cycles", "natural"):
            if k in row:
                row[k] = int(row[k]) + add
        out.append(dict(lane=ln["id"], part=a["part"], bus=a["bus"], member=n_old, rep=n_new, add=add, late=late))
        left = late_by_kit(row, fx + add, n_new, m)
        if left:
            raise MergeError(f"lane {ln['id']}: still {left:+d} off the table after pricing +{add}")
    return out


def dest_depth(typ, bus):
    """receiver IN-bus kit chain (deepest non-core internal_stations row; stage_kit_source_table_refresh._dest_depth)"""
    return max((len(e.get("regs_um", [])) for e in typ.get("internal_stations", [])
                if e.get("conn") == "bus:" + bus and not e.get("core")), default=0)


def late_by_kit(row, fixed, n, m):
    """predicted delivered - table cycles of a lane whose source kit chain is n and receiver IN chain m (LATCHECK
    side_stages with native_istations.annotate_kit): the source chain is cut from the receiver pad only when fixed >= n;
    a packed receiver pad >= 1 absorbs the receiver IN chain, a zero pad gets it kit-built."""
    cyc = int(row["cycles"])
    base = int(row.get("boundary", 2)) + int(row.get("stations", 0)) + int(row.get("clock_landing", 0))
    cut = n if fixed >= n else 0
    pad = max(0, cyc - base - cut)
    return base + n + pad + (0 if pad else m) - cyc


FT_PINS = ("in_face", "out_face", "width", "turnaround", "in_window_um", "out_window_um", "layer", "layers", "order",
           "in_layers", "out_layers", "in_order", "out_order")
FT_COUNT = ("stations_in",)


def ft_pin_key(s):
    """the pin interface of an ft slot (what a neighbour abuts); equal keys = one physical slot"""
    return json.dumps({k: s.get(k) for k in FT_PINS}, sort_keys=True)


def _ft_ends(s):
    lay = lambda side: set(s.get(f"{side}_layers") or s.get("layers") or ([s["layer"]] if s.get("layer") else []))
    return [(s["in_face"], s.get("in_window_um"), lay("in")), (s["out_face"], s.get("out_window_um"), lay("out"))]


def ft_overlaps(slots):
    """[(slot a, slot b, face)] class slot ends on one face whose windows and layer sets intersect"""
    out = []
    for i, a in enumerate(slots):
        for b in slots[i + 1:]:
            for fa, wa, la in _ft_ends(a):
                for fb, wb, lb in _ft_ends(b):
                    if fa == fb and wa and wb and max(wa[0], wb[0]) < min(wa[1], wb[1]) and (la & lb or not la or not lb):
                        out.append([a["name"], b["name"], fa])
    return out


SLOT_PIN = re.compile(r"^(fclk_in|cland_fstart_in|fclk_out|cland_fstart_out)_(.+)_(i|o)$")


def ft_class_name(name, key):
    """stable class name of a member slot whose own name is used by another pin set in the class"""
    return f"{name}_c{hashlib.sha1(key.encode()).hexdigest()[:6]}"


def slot_pins(lc, slots):
    """{pin name: slot} of a landing contract's per-ft-slot landing pins (fclk_in_<slot>_i, cland_fstart_out_<slot>_o..)"""
    out = {}
    for pin in lc.get("pins", []):
        m = SLOT_PIN.match(pin["name"])
        if m and m.group(2) in slots:
            out[pin["name"]] = m.group(2)
    return out


def ft_superset_plan(P, rep, members, rep_out):
    """-> dict(union=[class slots], ren={member: {old slot: class slot}}, pins={member: {old pin: class pin}},
    carry=[landing pin rows the class row gains]); refusals go to rep_out["refused"].
    Naming (stable, agreed with S81-LEAF-CLASS): a slot keeps its own name when the representative owns that name or
    no other pin set in the class uses it; otherwise it is <name>_c<sha1(pins)[:6]>.  Same pins = one slot."""
    cand = collections.defaultdict(list)            # pin key -> [(is_member, name, type, slot)]
    for tn in [rep] + members:
        for sl in P[tn].get("ft_slots", []):
            cand[ft_pin_key(sl)].append((tn != rep, sl["name"], tn, sl))
    keys_of = collections.defaultdict(set)
    for key, cs in cand.items():
        for c in cs:
            keys_of[c[1]].add(key)
    rep_names = {sl["name"] for sl in P[rep].get("ft_slots", [])}
    union, ren, taken, raise_ = [], {m: {} for m in members}, {}, {}
    st = lambda sl: int(sl.get("stations", 1))
    for key, cs in sorted(cand.items(), key=lambda kv: min((c[0], c[1]) for c in kv[1])):
        cs.sort(key=lambda c: (c[0], c[1]))
        keep = cs[0]
        name = keep[1] if (not keep[0] and keep[1] in rep_names) or len(keys_of[keep[1]]) == 1 \
            else ft_class_name(keep[1], key)
        row = max(cs, key=lambda c: (st(c[3]), -c[0]))[3]     # the deepest copy: same pins, most stations
        for is_m, old, tn, sl in cs:
            if any(json.dumps(sl.get(f)) != json.dumps(row.get(f)) for f in FT_COUNT):
                rep_out["refused"].append(f"{tn}: ft slot {old} has the pins of class slot {name} but other "
                                          f"stations_in")
            if is_m and old != name:
                ren[tn][old] = name
            if st(row) > st(sl):
                raise_[(tn, old)] = st(row) - st(sl)
        if name in taken:
            rep_out["refused"].append(f"ft slot class name {name} names two pin sets ({taken[name]}, {keep[2]})")
            continue
        taken[name] = keep[2]
        union.append(dict(copy.deepcopy(row), name=name))
    # per-slot landing pins follow their slot: renamed with it; the class row gains those it lacks
    rpins = {pin["name"] for pin in _lc(P[rep]).get("pins", [])}
    pins, carry = {}, []
    for m in members:
        lc = _lc(P[m]); slots = {sl["name"] for sl in P[m].get("ft_slots", [])}
        sp = slot_pins(lc, slots); pins[m] = {}
        for pin in lc.get("pins", []):
            if pin["name"] not in sp:
                continue
            g = SLOT_PIN.match(pin["name"])
            new = f"{g.group(1)}_{ren[m].get(sp[pin['name']], sp[pin['name']])}_{g.group(3)}"
            pins[m][pin["name"]] = new
            if new not in rpins:
                rpins.add(new); carry.append(dict(copy.deepcopy(pin), name=new))
    return dict(union=union, ren=ren, pins=pins, carry=carry, raise_=raise_)


def ft_superset_apply(plan, rep, members, fp, rep_out):
    """write the class slots + their landing pins, re-point renamed / collapsed slots' ports and landing edges,
    declare per-instance spare slots"""
    union, ren, pins = fp["union"], fp["ren"], fp["pins"]
    P = plan["partition_types"]; R = P[rep]
    if fp["carry"]:
        R.setdefault("clock", {}).setdefault("landing_contract", {}).setdefault("pins", []).extend(fp["carry"])
    pt0 = {p["name"]: p["type"] for p in plan["partitions"]}
    # same pins, fewer stations: the instance's lanes through that slot take the class station count (+cycles,
    # OWNER pre-approved); their latency rows move with it (schema lane_natural counts slot stations)
    lat = plan.get("latency", {}).get("lanes", {})
    port_lane = {pid: ln["id"] for ln in plan.get("lanes", []) for pid in ln.get("ports", [])}
    raised = []
    for pr in plan.get("ports", []):
        e = pr.get("dst") or {}
        b = e.get("bus", "")
        d = fp["raise_"].get((pt0.get(e.get("part")), b[:-2])) if b.endswith("_i") else None
        lid = port_lane.get(pr.get("id"))
        if d and lid:
            row = lat.get(lid)
            if row is not None:
                for k in ("cycles", "natural", "stations"):
                    if k in row:
                        row[k] = int(row[k]) + d
            raised.append(dict(lane=lid, part=e["part"], slot=b[:-2], add=d))
    rep_out["ft_stations_raised"] = raised
    edges = 0
    for e in (plan.get("clock") or {}).get("landing_network", {}).get("edges", []):
        for side in ("src", "dst"):
            x = e.get(side) or {}
            r = pins.get(pt0.get(x.get("part")))
            if r and x.get("bus") in r and r[x["bus"]] != x["bus"]:
                x["bus"] = r[x["bus"]]; edges += 1
    before = {s["name"] for s in R.get("ft_slots", [])}
    R["ft_slots"] = union
    if not R.get("superset"):
        R["superset"] = True
    part_type = {p["name"]: p["type"] for p in plan["partitions"]}
    used = collections.defaultdict(set); repointed = 0
    for pr in plan.get("ports", []):
        for side in ("src", "dst"):
            e = pr.get(side) or {}
            r = ren.get(part_type.get(e.get("part")))
            if r:
                for sfx in ("_i", "_o"):
                    b = e.get("bus", "")
                    if b.endswith(sfx) and b[:-2] in r:
                        e["bus"] = r[b[:-2]] + sfx; repointed += 1
            used[e.get("part")].add(e.get("bus"))
    spare = {}
    for p in plan["partitions"]:
        if p["type"] not in members and p["type"] != rep:
            continue
        r = ren.get(p["type"], {})
        old = [r.get(n, n) for n in p.get("spare_ends", [])]
        add = [s["name"] for s in union if not ({s["name"] + "_i", s["name"] + "_o"} & used[p["name"]])
               and s["name"] not in old]
        if add or old:
            p["spare_ends"] = sorted(set(old) | set(add))
        if add:
            spare[p["name"]] = add
    rep_out["ft_superset"] = dict(
        slots=len(union), added=sorted({s["name"] for s in union} - before),
        collapsed={m: r for m, r in ren.items() if r}, repointed_port_ends=repointed, spare=spare,
        landing_pins_added=[q["name"] for q in fp["carry"]], landing_edges_repointed=edges,
        overlaps=ft_overlaps(union))


def merge(plan, side, rep, members, role_strap=False, ft_superset=False):
    P = plan["partition_types"]
    if rep not in P:
        raise MergeError(f"representative {rep} is not a plan type")
    members = [m for m in members if m != rep]
    missing = [m for m in members if m not in P]
    if missing:
        raise MergeError(f"member types not in the plan: {missing}")
    R = P[rep]; rlc = _lc(R); rkeys = child_keys(rlc); rindex = {k: i for i, k in rkeys.items()}
    rep_out = dict(rep=rep, members=members, refused=[], moved={}, edges=dict(plan=0, sidecar=0), dropped=[])
    fp = ft_superset_plan(P, rep, members, rep_out) if ft_superset else None
    # ---- refusals first: nothing is written when any member is not a copy of the class row
    for m in members:
        t = P[m]
        for f in MUST_EQUAL:
            if f == "ft_slots" and ft_superset:
                continue
            if json.dumps(t.get(f), sort_keys=True) != json.dumps(R.get(f), sort_keys=True):
                rep_out["refused"].append(f"{m}: {f} differs from the representative")
        mlc = _lc(t)
        extra = data_landing_pins(mlc) - data_landing_pins(rlc) - (set(ROLE_PINS) if role_strap else set()) \
            - (set(fp["pins"][m]) if fp else set())
        if extra:
            rep_out["refused"].append(f"{m}: data landing pins not on the representative: {sorted(extra)[:6]}")
        for i, key in child_keys(mlc).items():
            if key not in rindex:
                rep_out["refused"].append(f"{m}: collector child {i} at {list(key[0])} seam={key[1]} is not a "
                                          f"representative child site")
    parts = [p for p in plan["partitions"] if p["type"] in members or p["type"] == rep]
    roles = {landing_role(side, p["name"]) for p in parts}
    if len(roles) > 1 and not role_strap:
        rep_out["refused"].append(f"count-aligned landing role differs between instances: {sorted(map(str, roles))} "
                                  f"(origin / relay strap needed)")
    if role_strap and len(roles) > 1:
        role_pins_union(P, rep, members, rep_out)
    if rep_out["refused"]:
        return rep_out
    if ft_superset:
        ft_superset_apply(plan, rep, members, fp, rep_out)
    # ---- class row: every representative child is tieable; seam children get a use strap pin
    if rkeys:
        tie = [dict(index=i, seam=k[1]) for i, k in sorted(rkeys.items())]
        rlc["tieable_children"] = tie
        rlc["pins"] = LTC.with_use_pins(rlc["pins"], tie, R["outline_um"])
    pads = [P[t].get("r8_strap_pad_max") for t in [rep] + members if P[t].get("r8_strap_pad_max") is not None]
    if pads:
        R["r8_strap_pad_max"] = max(pads)
    # ---- re-type every instance, re-index its incoming monitor edges by child site
    remap = {m: {i: rindex[k] for i, k in child_keys(_lc(P[m])).items()} for m in members}
    part_type = {p["name"]: p["type"] for p in plan["partitions"]}
    for e in (plan.get("clock") or {}).get("landing_network", {}).get("edges", []):
        mt = DN.match(e["dst"]["bus"]); tn = part_type.get(e["dst"]["part"])
        if mt and tn in remap:
            e["dst"]["bus"] = f"{mt.group(1)}_{remap[tn][int(mt.group(2))]}"; rep_out["edges"]["plan"] += 1
    coll = side.get("collector") or {}
    for e in coll.get("edges", []):
        if isinstance(e, dict) and part_type.get(e.get("dst")) in remap and e.get("dst_index") is not None:
            e["dst_index"] = remap[part_type[e["dst"]]][int(e["dst_index"])]; rep_out["edges"]["sidecar"] += 1
    rdepth = (coll.get("boot_budget") or {}).get("local_registered_depths", {})
    rep_parts = [p["name"] for p in plan["partitions"] if p["type"] == rep]
    before = {p["name"]: copy.deepcopy(P[p["type"]]) for p in plan["partitions"] if p["type"] in members}
    rep_depth = rdepth.get(rep_parts[0]) if rep_parts else None
    for p in plan["partitions"]:
        if p["type"] in members:
            rep_out["moved"][p["name"]] = p["type"]; p["type"] = rep
            row = (coll.get("parts") or {}).get(p["name"])
            if isinstance(row, dict) and "type" in row:
                row["type"] = rep
            if p["name"] in (coll.get("base_type_by_part") or {}):
                coll["base_type_by_part"][p["name"]] = (coll.get("types", {}).get(rep) or {}).get("base_type", rep)
            if p["name"] in rdepth and rep_depth is not None and rdepth[p["name"]] != rep_depth:
                rep_out.setdefault("boot_depth_changed", {})[p["name"]] = [rdepth[p["name"]], rep_depth]
                rdepth[p["name"]] = rep_depth
    rep_out["kit_priced"] = price_out_stations(plan, before)
    # ---- drop per-type die tables of the member types (the representative's apply to every instance)
    def drop(d, path):
        if isinstance(d, dict):
            for k in list(d):
                if k in members:
                    d.pop(k); rep_out["dropped"].append(f"{path}/{k}")
                else:
                    drop(d[k], f"{path}/{k}")
    drop({k: v for k, v in plan.items() if k not in ("partition_types", "partitions")}, "")
    drop(coll.get("types", {}), "/sidecar/collector/types")
    for m in members:
        del P[m]
    left = sorted(set(names_used(plan, set(members))) | set(names_used(side, set(members))))
    if left:
        raise MergeError(f"member type names still referenced after the merge: {left}")
    rep_out["instances"] = len(rep_parts) + len(rep_out["moved"])
    return rep_out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("side"); ap.add_argument("oplan"); ap.add_argument("oside")
    ap.add_argument("--rep")
    ap.add_argument("--reprice-from", help="only price OUT kit stations of PLAN instances whose type differs in this plan")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--members"); g.add_argument("--stem")
    ap.add_argument("--role-strap", action="store_true",
                    help="allow origin and relay copies in the class (landing_role_strap, strap_ca_relay)")
    ap.add_argument("--ft-superset", action="store_true",
                    help="class row = union of the members' ft slots (stable names, superset type, spare_ends)")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text()); side = json.loads(Path(a.side).read_text())
    if a.reprice_from:
        pre = json.loads(Path(a.reprice_from).read_text())
        pt0 = {p["name"]: p["type"] for p in pre["partitions"]}
        before = {p["name"]: pre["partition_types"][pt0[p["name"]]] for p in plan["partitions"]
                  if pt0.get(p["name"]) not in (None, p["type"])}
        try:
            rows = price_out_stations(plan, before)
        except MergeError as exc:
            print(f"CLASS-MERGE ERROR {exc}", file=sys.stderr); return 2
        if a.report:
            Path(a.report).write_text(json.dumps(dict(kit_priced=rows), indent=1) + "\n")
        Path(a.oplan).write_text(json.dumps(plan, indent=1) + "\n")
        Path(a.oside).write_text(json.dumps(side, separators=(",", ":")) + "\n")
        print(f"CLASS-MERGE reprice: {len(before)} re-typed instances, {len(rows)} lanes "
              f"+{sum(r['add'] for r in rows)} cycles")
        for r in rows:
            print("  KIT-PRICED", r)
        return 0
    if not a.rep or not (a.members or a.stem):
        ap.error("--rep and --members/--stem are required unless --reprice-from")
    members = (a.members.split(",") if a.members else
               sorted(k for k in plan["partition_types"] if k.split("__")[0] == a.stem))
    try:
        rep = merge(plan, side, a.rep, members, role_strap=a.role_strap, ft_superset=a.ft_superset)
    except MergeError as exc:
        print(f"CLASS-MERGE ERROR {exc}", file=sys.stderr); return 2
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if rep["refused"]:
        for r in rep["refused"]:
            print("CLASS-MERGE REFUSED", r, file=sys.stderr)
        return 2
    Path(a.oplan).write_text(json.dumps(plan, indent=1) + "\n")
    Path(a.oside).write_text(json.dumps(side, separators=(",", ":")) + "\n")
    print(f"CLASS-MERGE {a.rep}: {len(rep['members'])} member types -> 1, {rep['instances']} instances, "
          f"edges plan {rep['edges']['plan']} sidecar {rep['edges']['sidecar']}, dropped {len(rep['dropped'])} rows, "
          f"kit-priced {len(rep['kit_priced'])} lanes +{sum(r['add'] for r in rep['kit_priced'])} cycles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
