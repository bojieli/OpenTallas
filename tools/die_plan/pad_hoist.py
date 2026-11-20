#!/usr/bin/env python3
"""UNIFY-TOOLS pad_hoist (COORD ruling (b), 2026-11-20): move per-instance receiver lane pads out of a merged class.

A class merged into one type (class_merge.py) still binds as several modules when its instances land the same in-bus
with different receiver pads (bind u_lpad_<bus> D; e.g. QC sle_ctl x_su_l0_i: E 2/4, W 30/31).  This step keeps the
lane cycles and moves the per-instance part of the pad into ft slot stations on the lane's own path, so every instance
of the class keeps the class MINIMUM pad inside the partition and the difference sits in the ft partitions.

Input: the plan, the bind output dir of a strict bind of that plan (bind_report.json type_splits + the per-variant
rtl/<module>.sv u_lpad D values: the as-bound pads, after every kit/native station correction), and optionally the
types to fix (default: every TYPE_SPLIT type).  Rule per (type, slot) of an ft hop: its stations are one per-type
constant, so a hop takes k extra stations only when EVERY lane through that slot in EVERY instance of the hop type
still needs >= k (lanes outside the hoist set need 0, so a slot they share is never used).  Greedy until no progress;
the rest is reported as unplaced (exit 3, nothing written unless --partial).

Writes OUT_PLAN with ft_slots[].stations raised (+ a note), and a report {hoists, lanes, unplaced}.  The latency table
is left to gen.py latency (stations/natural rise, pad falls, cycles unchanged)."""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

LPAD = re.compile(r"ot_dp_dly\s*#\(\s*\.W\(\d+\),\s*\.D\((\d+)\)\)\s*u_lpad_(\w+)\s*\(")
INB = re.compile(r"^\s*input\s+wire\s+\[\d+:0\]\s+(\w+)\s*,?\s*//.*\blane\b", re.M)


def module_pads(text):
    """{in bus: receiver pad} of one bound module (in buses without u_lpad -> 0)"""
    pads = {m.group(1): 0 for m in INB.finditer(text)}
    for m in LPAD.finditer(text):
        pads[m.group(2)] = int(m.group(1))
    return pads


def bound_pads(bind_dir, types=None):
    """{type: {part: {in bus: pad}}} for the split types of a bind (variant k -> module T or T_v<k>)"""
    bd = Path(bind_dir)
    rep = json.loads((bd / "bind_report.json").read_text())
    out = {}
    for s in rep.get("type_splits", []):
        tn = s["type"]
        if types and tn not in types:
            continue
        out[tn] = {}
        for k, parts in enumerate(s["variants"]):
            mod = tn if k == 0 else f"{tn}_v{k}"
            pads = module_pads((bd / "rtl" / f"{mod}.sv").read_text())
            for p in parts:
                out[tn][p] = pads
    return out


def lane_paths(plan):
    """{(dst part, dst bus): (lane id, [(hop part, slot name)])} -- slot name as bind.plan_lanes"""
    ports = {x["id"]: x for x in plan.get("ports", [])}
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}
    slots = {tn: {f["name"]: f for f in t.get("ft_slots", [])} for tn, t in plan["partition_types"].items()}
    out = {}
    for ln in plan.get("lanes", []):
        hp = [ports[q] for q in ln["ports"]]
        hops = []
        for x, y in zip(hp, hp[1:]):
            part = x["dst"]["part"]
            ib, ob = x["dst"]["bus"], y["src"]["bus"]
            st = slots[ptype[part]]
            sl = st.get(ob.rsplit("_", 1)[0]) or st.get(ib.rsplit("_", 1)[0])
            hops.append((part, sl["name"] if sl else None))
        d = hp[-1]["dst"]
        out[(d["part"], d["bus"])] = (ln["id"], hops)
    return out


def in_station_floor(plan, tn, bus):
    """the receiver kit turns the bound pad of an IN bus into that bus's own internal_stations (kit_istations
    packed_input_delay), so the class pad never drops below their register count"""
    rows = [e for e in plan["partition_types"].get(tn, {}).get("internal_stations", [])
            if e.get("conn") == "bus:" + bus and not e.get("core")]
    return max((len(e.get("regs_um", [])) for e in rows), default=0)


def solve(plan, pads):
    """-> (hoists {(hop type, slot): k}, lanes {lane: dict}, unplaced [..]).  A (type, bus) whose differences cannot all
    be placed at the class minimum retries with a lower target (down to 0): then every instance hoists, and the hops of
    the instances that already sat at the minimum may be free where the others' are shared."""
    lower, final = defaultdict(int), set()
    while True:
        hoists, info, unplaced = _solve(plan, pads, lower)
        final |= {(u["type"], u["bus"]) for u in unplaced if u["below"]}     # lowering cannot pass the floor
        bad = {(u["type"], u["bus"]) for u in unplaced} - final
        if not bad:
            return hoists, info, unplaced
        for k in bad:
            if any(u["target"] > in_station_floor(plan, *k) for u in unplaced if (u["type"], u["bus"]) == k):
                lower[k] += 1
            else:                       # even target 0 does not place it: keep the class minimum, report it
                lower[k] = 0
                final.add(k)


def _solve(plan, pads, lower):
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}
    paths = lane_paths(plan)
    need = {}                                   # lane id -> remaining cycles to hoist
    info = {}
    for tn, by_part in sorted(pads.items()):
        buses = sorted({b for v in by_part.values() for b in v})
        for b in buses:
            vals = {p: v.get(b, 0) for p, v in by_part.items()}
            if len(set(vals.values())) < 2:
                continue
            floor = in_station_floor(plan, tn, b)
            m = max(floor, min(vals.values()) - lower[(tn, b)])
            for p, v in sorted(vals.items()):
                if v < m:                       # below the kit IN-station floor: only +cycles can level it
                    lid = paths.get((p, b), ("?",))[0]
                    need[lid] = 1
                    info[lid] = dict(type=tn, part=p, bus=b, pad=v, target=m, hops=[], below=True)
                    continue
                if v == m:
                    continue
                lp = paths.get((p, b))
                if lp is None:
                    need[f"?{p}.{b}"] = v - m
                    info[f"?{p}.{b}"] = dict(type=tn, part=p, bus=b, pad=v, target=m, hops=[])
                    continue
                need[lp[0]] = v - m
                info[lp[0]] = dict(type=tn, part=p, bus=b, pad=v, target=m, hops=[list(h) for h in lp[1]])
    users = defaultdict(list)                   # (hop type, slot) -> every lane through it, any instance
    for (dp, db), (lid, hops) in paths.items():
        for part, sl in hops:
            if sl:
                users[(ptype[part], sl)].append(lid)
    hoists = defaultdict(int)
    progress = True
    while progress:
        progress = False
        for lid in sorted(need):
            if need[lid] <= 0 or lid.startswith("?") or info[lid].get("below"):
                continue
            for part, sl in info[lid]["hops"]:
                if not sl:
                    continue
                key = (ptype[part], sl)
                k = min(need.get(u, 0) for u in users[key])
                if k > 0:
                    hoists[key] += k
                    for u in users[key]:
                        need[u] -= k
                    progress = True
                    break
    unplaced = [dict(lane=l, left=n, below=bool(info[l].get("below")),
                     **{x: info[l][x] for x in ("type", "part", "bus", "pad", "target")})
                for l, n in sorted(need.items()) if n > 0]
    for l in info:
        info[l]["hoisted"] = 0 if info[l].get("below") else info[l]["pad"] - info[l]["target"] - max(need.get(l, 0), 0)
    return dict(hoists), info, unplaced


def apply(plan, hoists, tag="UNIFY-TOOLS pad_hoist"):
    """raise the slot stations and keep the latency table in step (bind LANE_LATENCY): every lane through a raised
    (type, slot) hop gets stations/natural + k and pad - k; its cycles are unchanged"""
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}
    lat = plan.get("latency", {}).get("lanes", {})
    stale = []
    lanes_raw = {x["id"]: x for x in plan.get("lanes", [])}
    for (dp, db), (lid, hops) in lane_paths(plan).items():
        add = sum(hoists.get((ptype[part], sl), 0) for part, sl in hops if sl)
        row = lat.get(lid)
        if not add or row is None:
            continue
        # the hoisted cycles come out of the AS-BOUND receiver pad.  A table pad below it means the row's fixed cycles
        # still count internal stations of the MEMBER type that the merged (representative) type does not have (the
        # bind lands them as receiver pad): those fixed cycles are cut so natural = boundary + stations + fixed +
        # clock_landing stays <= cycles (plan_gate FIXEDCYC); cycles never change here.  Listed as stale rows.
        row["stations"] = int(row.get("stations", 0)) + add
        cyc = int(row["cycles"])
        nat = int(row.get("boundary", 2)) + row["stations"] + int(row.get("fixed", 0)) + int(row.get("clock_landing", 0))
        cut = max(0, nat - cyc)
        if cut:
            if int(row.get("fixed", 0)) < cut:
                raise ValueError(f"pad_hoist: lane {lid}: {add} hoisted stations exceed its cycles {cyc}")
            row["fixed"] = int(row["fixed"]) - cut
            stale.append(dict(lane=lid, table_pad=int(row.get("pad", 0)), hoisted=add, fixed_cut=cut))
            nat = cyc
        row["natural"] = nat
        row["pad"] = cyc - nat
    for (tn, sl), k in sorted(hoists.items()):
        s = next(f for f in plan["partition_types"][tn]["ft_slots"] if f["name"] == sl)
        old = int(s.get("stations", 0))
        s["stations"] = old + k
        s["note"] = (s.get("note", "") + "; " if s.get("note") else "") + \
            f"{tag}: stations {old} -> {old + k} (per-instance receiver pad hoisted out of a merged class)"
    return stale


def raise_cycles(plan, pads, unplaced):
    """fallback for a (type, bus) no free slot can level (its only hop is itself a class type or a shared type, e.g. QC
    slw_fw x_ctl_p1_i through slw_stm): level UP instead -- every instance lane whose pad is below the bus maximum gets
    +cycles (and +pad) so all land the same receiver pad (OWNER: +cycles pre-approved).  -> [{lane, add}]"""
    paths = lane_paths(plan)
    lat = plan.get("latency", {}).get("lanes", {})
    out = []
    for tn, b in sorted({(u["type"], u["bus"]) for u in unplaced}):
        vals = {q: v.get(b, 0) for q, v in pads[tn].items()}
        M = max(vals.values())
        if any(u.get("below") for u in unplaced if (u["type"], u["bus"]) == (tn, b)):
            M = max(u["target"] for u in unplaced if (u["type"], u["bus"]) == (tn, b))
        for q, v in sorted(vals.items()):
            lid = paths[(q, b)][0]
            if v < M and lid in lat:
                row = lat[lid]
                row["cycles"] = int(row["cycles"]) + (M - v)
                row["pad"] = int(row.get("pad", 0)) + (M - v)
                out.append(dict(type=tn, bus=b, lane=lid, add=M - v))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("bind_dir")
    ap.add_argument("out_plan")
    ap.add_argument("--types", default="", help="comma list; default every TYPE_SPLIT type of the bind")
    ap.add_argument("--report")
    ap.add_argument("--partial", action="store_true", help="write the plan even when some pad is unplaced")
    ap.add_argument("--raise-cycles", action="store_true",
                    help="level the unplaced buses UP: +cycles on the lanes of the lower instances")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    pads = bound_pads(a.bind_dir, set(filter(None, a.types.split(","))) or None)
    hoists, lanes, unplaced = solve(plan, pads)
    rep = dict(types=sorted(pads), hoists=[dict(type=t, slot=s, add=k) for (t, s), k in sorted(hoists.items())],
               lanes=lanes, unplaced=unplaced)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"pad_hoist: {len(pads)} types, {len(lanes)} lanes, {len(hoists)} slot raises "
          f"(+{sum(hoists.values())} stations), {len(unplaced)} unplaced")
    for u in unplaced:
        print("  UNPLACED", u)
    if unplaced and a.raise_cycles:
        # the unplaced buses are not hoisted at all (their slots stay); the lower instances rise to the maximum
        keep = {(u["type"], u["bus"]) for u in unplaced}
        pads2 = {tn: {q: {b: v for b, v in bs.items() if (tn, b) not in keep} for q, bs in d.items()}
                 for tn, d in pads.items()}
        hoists, lanes, rest = solve(plan, pads2)
        assert not rest, rest
        rep.update(hoists=[dict(type=t, slot=s, add=k) for (t, s), k in sorted(hoists.items())], lanes=lanes)
        rep["raised_cycles"] = raise_cycles(plan, pads, unplaced)
        print(f"  raise-cycles: {len(rep['raised_cycles'])} lanes +{sum(r['add'] for r in rep['raised_cycles'])} cycles")
        unplaced = []
    if unplaced and not a.partial:
        return 3
    rep["stale_table_rows"] = apply(plan, hoists)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    Path(a.out_plan).write_text(json.dumps(plan, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
