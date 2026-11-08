#!/usr/bin/env python3
"""DIE-HBM-91-REACH 11-08: plan event that adds FIRM internal stations + PIN CYCLES on long type buses (istareach).

Cause (DIE-HBM-91-REACH RESULT 11-08): after istadrop_1107 the re-routed buses of 25 HBM types carry no internal
stations; 379 face -> leaf links are > 450 um (q_su31 L5032_o ~2 mm, hub links up to ~11 mm), and the timing estimate
(0.76 ps/um, 833 ps) misses setup on 368 of them.  check.py R3-INTERNAL does not see them (the buses carry no `leaf`).

For every data bus B of a selected type T (face + window, no bus:B entry yet) the tool finds the bound leaves of B in the
bound RTL of record (in bus: instances reading B_q; out bus: instances driving the w_* wires of u_bout_B.d) and their
plan boxes (hard_cores / contents), and measures the face-window centre -> nearest box point (Manhattan) per leaf.
A bus whose farthest leaf is <= REACH (405 um, R3-INTERNAL / ft_station_max_um) is left alone.  Otherwise:

  ONE chain (station form of today's tools: kit_istations.bus_entries merges a bus into one chain) when every leaf is
  within one reach of one chain end: chain end C = the Manhattan centre of the leaf points (single leaf: the leaf
  point); regs_um = hub_repack.route_station(Raster(hard cores + halo), face point, C, 0, REACH) (+ a register at C
  when a leaf is otherwise > REACH from the last register).  Every hop face -> regs -> each leaf is checked <= REACH.
  Entry: conn bus:B, from_um face point, to_um farthest leaf point, regs_um face -> leaf order, bits, launch
  "face bus B", capture <leaf plan inst> (out buses keep the same face -> leaf geometry, as the planner writes them;
  kit_istations puts stage 0 at the leaf side).

PIN CYCLES: each lane whose source end (out bus) or destination end (in bus) gets n stations gets fixed_cycles += n,
so fixed_cycles = source stations + destination stations (native_istations.annotate rule).  latency.lanes is updated
by the delta of gen.latency_table (schema.Plan) between the input and the output plan, so R8 group pads follow.
Bind: an in-bus pad lands at the destination (bind.py lane_pad -> u_lpad_<B>, which kit_istations.packed_input_delay
pins at regs_um); an out-bus pad must be at the SOURCE, which needs asbuilt internal_stations_types (native_istations:
source stations materialised in the bind, destination pad cut by internal_source_cycles).  The ledger lists those
types (`native_types`).

NOT stationed (listed in the ledger with the reason, nothing changed for them):
  branch        leaves farther apart than one chain end can serve (needs per-leaf chains or a face-port re-site)
  no_face_reg   the bound RTL has no u_bin_B / u_bout_B face register (registered hard pin: the bind lands no pad)
  out_native    out bus of a type whose EXISTING out entries break the native rule (fixed_cycles != stations), so the
                type cannot be put in internal_stations_types without repricing those entries
  out_lanes     out bus with != 1 outgoing lane on a partition of the type (native_istations refuses it)
  in_lanes      in bus with != 1 landing lane
  fixed         lane already has fixed_cycles (left to its owner)
  route         no legal chain with every hop <= REACH

    add_reach_istations.py PLAN_IN PLAN_OUT LEDGER --bound-rtl DIR --types T1,T2,... [--reach 405]
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REACH = 405.0
CENTRE_MARGIN = 0.9          # one chain only when the leaf points fit in a Manhattan ball of 0.9 x REACH


def sv(s):
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", s)).strip("_")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def inst_bodies(txt):
    """{instance: port-connection text}; a body never crosses a ';' (reach.py's lazy multi-line match swallowed the
    first multi-line instance after a run of one-line face registers)"""
    return {m.group(2): m.group(3) for m in re.finditer(
        r"^[ \t]+(\w+)(?:[ \t]+#\([^;]*?\))?[ \t]+(u_\w+)[ \t]*\(([^;]*)\)[ \t]*;", txt, re.M)}


def bus_leaves(txt, inst, b):
    """bound instance names that read (in) / drive (out) bus b"""
    n = b["name"]
    out = set()
    if b["dir"] == "out":
        m = re.search(rf"u_bout_{re.escape(n)}\s*\(.*?\.d\((.*?)\),\s*\.ea", txt, re.S)
        wires = set(re.findall(r"\b(w_\w+?)\[", m.group(1))) if m else set()
        for k, body in inst.items():
            if any(re.search(rf"\b{re.escape(w)}\b", body) for w in wires):
                out.add(k)
    else:
        for k, body in inst.items():
            if k.startswith(("u_bin_", "u_bout_")):
                continue
            if re.search(rf"\b{re.escape(n)}_q\b", body):
                out.add(k)
    return out


def leaf_points(t, leaves, P):
    """{plan inst: nearest box point to P} for the plan boxes of the bound leaves (reach.py matching)"""
    boxes = {}
    for c in (t.get("hard_cores") or []) + (t.get("contents") or []):
        if "origin_um" in c and "outline_um" in c:
            x0, y0 = c["origin_um"]
            boxes[sv("u_" + c["inst"])] = (c["inst"], (x0, y0, x0 + c["outline_um"][0], y0 + c["outline_um"][1]))
    pts = {}
    for lf in sorted(leaves):
        key = lf[2:] if lf.startswith("u_u_") else lf
        for bn, (pi, (x0, y0, x1, y1)) in sorted(boxes.items()):
            if bn == sv(lf) or bn.startswith(sv(lf) + "_") or bn == key or bn.startswith(key + "_"):
                q = (min(max(P[0], x0), x1), min(max(P[1], y0), y1))
                if pi not in pts or man(P, q) > man(P, pts[pi]):
                    pts[pi] = q
    return pts


def face_point(t, b):
    W, H = t["outline_um"]
    c = sum(b["window_um"]) / 2
    return {"N": (c, H), "S": (c, 0.0), "W": (0.0, c), "E": (W, c)}[b["face"]]


def free_near(HR, R, C, rings=200):
    """C itself when hub_repack.escape finds a free lattice point for it, else the nearest free lattice point on
    square rings around C (escape recurses without end when C sits deep in a block of abutted cores, d44v main
    after expx328), else None"""
    try:
        e = HR.escape(R, tuple(C))
        if R.free(*e):
            return e
    except RecursionError:
        pass
    x, y = HR.sn(C[0]), HR.sn(C[1])
    for d in range(1, rings):
        ring = sorted({(i, j) for i in range(-d, d + 1) for j in (-d, d)} | {(i, j) for j in range(-d, d + 1) for i in (-d, d)},
                      key=lambda ij: (abs(ij[0]) + abs(ij[1]), ij))
        for i, j in ring:
            q = (x + i * HR.G, y + j * HR.G)
            if 0 <= q[0] <= R.W and 0 <= q[1] <= R.H and R.free(*q):
                return q
    return None


def chain(t, P, pts, reach):
    """(regs, to_um) of one chain face P -> leaves, every hop <= reach, or None"""
    import hub_repack as HR
    W, H = t["outline_um"]
    R = HR.Raster(W, H, [HR._core_rect(h) for h in t.get("hard_cores", [])])
    us = [x + y for x, y in pts.values()]
    vs = [x - y for x, y in pts.values()]
    if len(pts) == 1:
        C = next(iter(pts.values()))
    else:
        cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
        C = ((cu + cv) / 2, (cu - cv) / 2)
    C = free_near(HR, R, C)
    if C is None:
        return None
    r = HR.route_station(R, list(P), list(C), 0, reach)
    if r is None:
        return None
    regs = [list(x) for x in r["regs"]]
    last = regs[-1] if regs else P
    if max(man(last, q) for q in pts.values()) > reach + 1e-6:
        regs.append([C[0], C[1]])
    seq = [list(P)] + regs
    if any(man(a, b) > reach + 1e-6 for a, b in zip(seq, seq[1:])):
        return None
    if not regs or max(man(regs[-1], q) for q in pts.values()) > reach + 1e-6:
        return None
    far = max(sorted(pts), key=lambda k: man(regs[-1], pts[k]))
    return regs, list(pts[far]), far


def lane_maps(raw):
    lane_of = {}
    for L in raw.get("lanes", []):
        for pid in L["ports"]:
            lane_of[pid] = L["id"]
    first = {L["id"]: L["ports"][0] for L in raw.get("lanes", [])}
    last = {L["id"]: L["ports"][-1] for L in raw.get("lanes", [])}
    ports = {q["id"]: q for q in raw.get("ports", [])}
    return lane_of, first, last, ports


def bus_lanes(raw, maps, parts, B, d):
    """{partition: set(lane ids)} whose source (out) / destination (in) end is bus B of the partition"""
    lane_of, first, last, ports = maps
    out = {}
    for pn in parts:
        ls = set()
        for lid, pid in (first if d == "out" else last).items():
            e = ports[pid]["src" if d == "out" else "dst"]
            if e.get("part") == pn and e.get("bus") == B:
                ls.add(lid)
        out[pn] = ls
    return out


def far_end_stations(raw, maps, lid):
    """stations already declared on the destination bus of lane lid (native rule receiver count)"""
    lane_of, first, last, ports = maps
    dst = ports[last[lid]]["dst"]
    ptype = {p["name"]: p["type"] for p in raw.get("partitions", [])}
    tt = raw["partition_types"].get(ptype.get(dst.get("part")), {})
    return sum(len(x["regs_um"]) for x in tt.get("internal_stations", []) if x.get("conn") == "bus:" + dst.get("bus", ""))


def native_ok_existing(raw, tn, maps, parts):
    """True when every existing out bus: entry of tn satisfies the native rule fixed_cycles == source + receiver"""
    t = raw["partition_types"][tn]
    buses = {b["name"]: b for b in t.get("buses", [])}
    fixed = {L["id"]: int(L.get("fixed_cycles", 0)) for L in raw.get("lanes", [])}
    lane_of, first, last, ports = maps
    T = raw["partition_types"]
    ptype = {p["name"]: p["type"] for p in raw.get("partitions", [])}
    for e in t.get("internal_stations", []):
        c = e.get("conn", "")
        if not c.startswith("bus:") or buses.get(c[4:], {}).get("dir") != "out":
            continue
        for pn, ls in bus_lanes(raw, maps, parts, c[4:], "out").items():
            if len(ls) != 1:
                return False
            lid = next(iter(ls))
            dst = ports[last[lid]]["dst"]
            tt = T.get(ptype.get(dst.get("part")), {})
            rec = {len(x["regs_um"]) for x in tt.get("internal_stations", []) if x.get("conn") == "bus:" + dst.get("bus", "")}
            if len(rec) > 1 or fixed[lid] != len(e["regs_um"]) + next(iter(rec), 0):
                return False
    return True


def lat_delta(raw0, raw1):
    import schema as S
    import gen
    t0 = gen.latency_table(S.Plan(raw0))
    t1 = gen.latency_table(S.Plan(raw1))
    return {k: (t0[k], t1[k]) for k in t1 if t0.get(k) != t1[k]}


def apply(raw, rtl_dir, types, reach=REACH):
    from drop_dead_istations import bound_rtl_file
    T = raw["partition_types"]
    parts_of = collections.defaultdict(list)
    for p in raw.get("partitions", []):
        parts_of[p["type"]].append(p["name"])
    maps = lane_maps(raw)
    fixed = {L["id"]: int(L.get("fixed_cycles", 0)) for L in raw.get("lanes", [])}
    unknown = sorted(set(types) - set(T))
    if unknown:
        raise SystemExit(f"add_reach_istations: unknown types {unknown}")
    rows, adds, add_lane = [], collections.defaultdict(list), collections.Counter()
    native_types = set()
    for tn in sorted(types):
        t = T[tn]
        f = bound_rtl_file(rtl_dir, raw, tn)
        if f is None:
            raise SystemExit(f"add_reach_istations: {tn}: no bound RTL in {rtl_dir}")
        txt = Path(f).read_text()
        inst = inst_bodies(txt)
        have = {e.get("conn") for e in t.get("internal_stations", [])}
        nat_ok = native_ok_existing(raw, tn, maps, parts_of[tn])
        for b in t.get("buses", []):
            if b.get("kind") != "data" or not b.get("window_um") or "face" not in b or ("bus:" + b["name"]) in have:
                continue
            B, d = b["name"], b["dir"]
            P = face_point(t, b)
            pts = leaf_points(t, bus_leaves(txt, inst, b), P)
            if not pts:
                continue
            L = max(man(P, q) for q in pts.values())
            if L <= reach:
                continue
            row = dict(type=tn, bus=B, dir=d, bits=b["width"], length_um=round(L, 1), leaves=sorted(pts))
            us = [x + y for x, y in pts.values()]
            vs = [x - y for x, y in pts.values()]
            rad = max(max(us) - min(us), max(vs) - min(vs)) / 2
            lanes = bus_lanes(raw, maps, parts_of[tn], B, d)
            nl = sorted(x for s in lanes.values() for x in s)
            row["lanes"] = nl
            why = None
            if rad > CENTRE_MARGIN * reach:
                why = f"branch: leaves span a Manhattan radius {rad:.0f} um > {CENTRE_MARGIN * reach:.0f}"
            elif not re.search(rf"\bu_b{'in' if d == 'in' else 'out'}_{re.escape(B)}\s*\(", txt):
                why = "no_face_reg: no face register in the bound RTL (registered hard pin)"
            elif any(len(s) != 1 for s in lanes.values()):
                why = f"{d}_lanes: {sorted(len(s) for s in lanes.values())} lanes per partition"
            elif d == "out" and not nat_ok:
                why = "out_native: existing out entries of the type break fixed_cycles == stations"
            elif any(fixed[x] for x in nl):
                why = "fixed: lane already has fixed_cycles"
            elif d == "out" and any(far_end_stations(raw, maps, x) for x in nl):
                why = "out_receiver: the destination bus already has (unpriced) internal stations"
            if why is None:
                c = chain(t, P, pts, reach)
                if c is None:
                    why = "route: no chain with every hop <= reach"
            if why:
                row["verdict"], row["reason"] = "SKIP", why
                rows.append(row)
                continue
            regs, to, far = c
            n = len(regs)
            e = dict(conn="bus:" + B, from_um=[round(P[0], 3), round(P[1], 3)], to_um=[round(to[0], 3), round(to[1], 3)],
                     regs_um=[[round(x, 3), round(y, 3)] for x, y in regs], bits=int(b["width"]),
                     launch="face bus " + B, capture=far,
                     note=f"istareach_1108 (DIE-HBM-91-REACH): {L:.0f} um face -> leaf, {len(pts)} leaf box(es), "
                          f"{n} station(s), hops <= {reach:g} um; PIN CYCLES +{n} on {','.join(nl)}")
            adds[tn].append(e)
            for x in nl:
                add_lane[x] += n
            if d == "out":
                native_types.add(tn)
            row.update(verdict="ADD", stations=n, chain_end=far, regs_um=e["regs_um"])
            rows.append(row)
    raw0 = json.loads(json.dumps(raw))
    for tn, es in adds.items():
        T[tn].setdefault("internal_stations", []).extend(es)
    for L in raw.get("lanes", []):
        if add_lane.get(L["id"]):
            L["fixed_cycles"] = int(L.get("fixed_cycles", 0)) + add_lane[L["id"]]
    delta = lat_delta(raw0, raw)
    tab = raw.get("latency", {}).get("lanes", {})
    for lid, (a, b_) in delta.items():
        if lid in tab:
            for k in ("cycles", "fixed", "natural", "pad"):
                if k in a and k in b_:
                    tab[lid][k] = tab[lid].get(k, a[k]) + (b_[k] - a[k])
    ledger = dict(schema="opentallas.add_reach_istations.v1", event="istareach_1108", reach_um=reach,
                  bound_rtl=str(rtl_dir), types=sorted(types),
                  added_entries=sum(len(v) for v in adds.values()),
                  added_stations=sum(len(e["regs_um"]) for v in adds.values() for e in v),
                  lanes_fixed_cycles={k: v for k, v in sorted(add_lane.items())},
                  native_types=sorted(native_types),
                  latency_delta={k: dict(param=b_.get("param"), cycles=[a["cycles"], b_["cycles"]],
                                         fixed=[a.get("fixed"), b_.get("fixed")]) for k, (a, b_) in sorted(delta.items())},
                  skipped=collections.Counter(r["reason"].split(":")[0] for r in rows if r["verdict"] == "SKIP"),
                  rows=rows)
    return raw, ledger


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("ledger")
    ap.add_argument("--bound-rtl", required=True)
    ap.add_argument("--types", required=True)
    ap.add_argument("--reach", type=float, default=REACH)
    a = ap.parse_args(argv)
    if not 0 < a.reach <= REACH:
        raise SystemExit("add_reach_istations: reach must respect the <= 405 um rule")
    raw = json.load(open(a.plan_in))
    raw, ledger = apply(raw, a.bound_rtl, [x for x in a.types.split(",") if x], a.reach)
    note = (f"DIE-HBM-91-REACH istareach_1108 ({ledger['added_entries']} internal_stations entries, "
            f"{ledger['added_stations']} stations, PIN CYCLES on {len(ledger['lanes_fixed_cycles'])} lanes)")
    raw["note"] = note + " <- " + raw.get("note", "") if raw.get("note") else note
    Path(a.plan_out).write_text(json.dumps(raw))
    Path(a.ledger).write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    print(note, json.dumps(dict(skipped=ledger["skipped"], native_types=ledger["native_types"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
