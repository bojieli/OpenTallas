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
is left to gen.py latency (stations/natural rise, pad falls, cycles unchanged).

UNIFY-TOOLS-R3: a raised slot is re-sited (resite_slots) so its sites match the new count (schema: len(regs_um) ==
stations, bit_sites_um = stations - 1 internal stages, G0 refuses anything else).  A slot with planned per-bit sites
keeps them (they follow the slot's own, often macro-avoiding, route) and each added stage splits the longest hop at
its per-bit midpoint, snapped to the sites' own row / site grid (split_sites).  A slot with only regs_um is re-sited
by station_rule.slot_row (LOCKUP-STATION rule: stage 0 at the in pin, stage j at j / n of each bit's pin -> pin route).
    pad_hoist.py PLAN - OUT_PLAN --resite-only [--no-snap]   re-site every slot whose site count != stations"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


class CutError(ValueError):
    """a hoist would cut a lane's fixed cycles below the kit stations they price"""


def kit_floor(plan, lid):
    """registers of the source type's OUT-bus and the destination type's IN-bus internal_stations on this lane"""
    ports = {x["id"]: x for x in plan.get("ports", [])}
    ln = next(x for x in plan["lanes"] if x["id"] == lid)
    a, b = ports[ln["ports"][0]]["src"], ports[ln["ports"][-1]]["dst"]
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}

    def regs(part, bus):
        rows = plan["partition_types"][ptype[part]].get("internal_stations", [])
        return max((len(e.get("regs_um", [])) for e in rows if e.get("conn") == "bus:" + bus), default=0)
    return regs(a["part"], a["bus"]) + regs(b["part"], b["bus"])


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
            # the cut may not go below the kit stations the fixed cycles still price (native_istations: raw lane
            # fixed_cycles >= kit depth); raw fixed_cycles and the row move together (plan_gate FIXEDCYC)
            if int(row.get("fixed", 0)) - cut < kit_floor(plan, lid):
                raise CutError(lid)
            row["fixed"] = int(row["fixed"]) - cut
            if lid in lanes_raw and "fixed_cycles" in lanes_raw[lid]:
                lanes_raw[lid]["fixed_cycles"] = row["fixed"]
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


def stale_slots(plan):
    """[(type, slot)] whose regs_um / bit_sites_um count does not match its stations"""
    out = []
    for tn, t in sorted(plan["partition_types"].items()):
        for sl in t.get("ft_slots", []) or []:
            n = int(sl.get("stations", 1))
            bs = sl.get("bit_sites_um")
            if ("regs_um" in sl and len(sl["regs_um"]) != n) or (
                    bs is not None and len(bs) != n - 1 and not (sl.get("explicit_stage0") and len(bs) == n)):
                out.append((tn, sl["name"]))
    return out


SITE_W, ROW_H = 0.054, 0.27


def _hop(a, b):
    return max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(a, b))


def split_sites(s):
    """add the missing stages of a slot that has per-bit sites: each one at the per-bit midpoint of the longest hop
    between consecutive stages (stage 0 = the first internal stage moved back by regs_um[1] - regs_um[0] when it has
    no own sites), snapped to the grid of the slot's existing sites, a taken site moved one site column.
    -> worst hop (um) after"""
    regs, bs = [list(r) for r in s["regs_um"]], [[list(p) for p in st] for st in s["bit_sites_um"]]
    n = int(s.get("stations", 1))
    own0 = bool(s.get("explicit_stage0")) and len(bs) == len(regs)
    if own0:
        stages = bs
    else:
        dx, dy = regs[0][0] - regs[1][0], regs[0][1] - regs[1][1]
        stages = [[[x + dx, y + dy] for x, y in bs[0]]] + bs
    x0, y0 = bs[0][0][0] % SITE_W, bs[0][0][1] % ROW_H
    taken = {(round((x - x0) / SITE_W), round((y - y0) / ROW_H)) for st in bs for x, y in st}
    while len(stages) < n:
        j = max(range(len(stages) - 1), key=lambda i: _hop(stages[i], stages[i + 1]))
        new = []
        for (ax, ay), (bx, by) in zip(stages[j], stages[j + 1]):
            c, r = round(((ax + bx) / 2 - x0) / SITE_W), round(((ay + by) / 2 - y0) / ROW_H)
            while (c, r) in taken:
                c += 1
            taken.add((c, r))
            new.append([round(x0 + c * SITE_W, 6), round(y0 + r * ROW_H, 6)])
        stages.insert(j + 1, new)
    cen = [[round(sum(p[0] for p in st) / len(st), 4), round(sum(p[1] for p in st) / len(st), 4)] for st in stages]
    if own0:
        s["bit_sites_um"], s["regs_um"] = stages, cen
    else:
        s["bit_sites_um"], s["regs_um"] = stages[1:], [regs[0]] + cen[1:]
    return round(max(_hop(a, b) for a, b in zip(stages, stages[1:])), 1) if len(stages) > 1 else 0.0


def resite_slots(plan, keys, snap=True):
    """re-site the given (type, slot)s at their current station count (station_rule.slot_row) -> [{type, slot,
    stations, form, worst_hop_um}]; a slot the rule cannot site keeps its count and is reported form=unsited"""
    import schema as S
    import station_rule as SR
    if not keys:
        return []
    try:
        P = S.Plan(plan)
    except Exception:          # a plan schema.Plan cannot load (unit fixtures): window-centre pins, no tap grid
        P = None
    out = []
    for tn in sorted({k[0] for k in keys}):
        t = plan["partition_types"][tn]
        try:
            taps = S.tap_grid(P, tn) if P is not None else []
        except Exception:
            taps = []
        cache = {}
        for s in t.get("ft_slots", []):
            if (tn, s["name"]) not in keys or ("regs_um" not in s and "bit_sites_um" not in s):
                continue                # a slot without planned sites has nothing to re-site
            n = int(s.get("stations", 1))
            if s.get("bit_sites_um") and len(s.get("regs_um", [])) >= 2 and len(s["regs_um"]) < n:
                worst = split_sites(s)
                out.append(dict(type=tn, slot=s["name"], stations=n, form="split", worst_internal_hop_um=worst))
                continue
            try:
                pins = SR._plan_pins(P, tn, s) if P is not None else (None, None)
            except Exception:
                pins = (None, None)
            sn = (lambda ideal, _t=t, _c=cache: SR._snap(ideal, _t, _c)) if snap else None
            r = SR.slot_row(tn, t, s, pins=pins if pins[0] else None, taps=taps, snap=sn)
            n = int(s.get("stations", 1))
            if len(r["regs_um"]) != n:
                out.append(dict(type=tn, slot=s["name"], stations=n, form="unsited"))
                continue
            s["regs_um"] = r["regs_um"]
            s["bit_sites_um"] = r["bit_sites_um"]
            s["bit_site_cell_um"] = list(SR.CELL)
            s["explicit_stage0"] = True
            s["keep_firm"] = True
            out.append(dict(type=tn, slot=s["name"], stations=n, form=r["site_form"], worst_hop_um=r["worst_hop_um"],
                            snapped=r["snapped"]))
    return out


def raise_cycles(plan, pads, unplaced):
    """fallback for a (type, bus) no free slot can level (its only hop is itself a class type or a shared type, e.g. QC
    slw_fw x_ctl_p1_i through slw_stm): level UP instead -- every instance lane whose pad is below the bus maximum gets
    +cycles (and +pad) so all land the same receiver pad (OWNER: +cycles pre-approved).  -> [{lane, add}]"""
    paths = lane_paths(plan)
    lat = plan.get("latency", {}).get("lanes", {})
    out = []
    for tn, b in sorted({(u["type"], u["bus"]) for u in unplaced}):
        vals = {q: v.get(b, 0) for q, v in pads[tn].items()}
        M = max(max(vals.values()), in_station_floor(plan, tn, b))
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
    ap.add_argument("--resite-only", action="store_true",
                    help="only re-site every slot whose site count != stations (bind_dir unused, give -)")
    ap.add_argument("--no-snap", action="store_true", help="re-site at the ideal route points (no row-site snap)")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    if a.resite_only:
        rs = resite_slots(plan, set(stale_slots(plan)), snap=not a.no_snap)
        left = stale_slots(plan)
        if a.report:
            Path(a.report).write_text(json.dumps(dict(resited=rs, still_stale=left), indent=1) + "\n")
        print(f"pad_hoist resite: {len(rs)} slots re-sited, {len(left)} still stale")
        for r in rs:
            print("  RESITE", r)
        Path(a.out_plan).write_text(json.dumps(plan, indent=1) + "\n")
        return 3 if left else 0
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
    import copy
    keep = set()
    base = plan
    while True:
        plan = copy.deepcopy(base)
        if unplaced and a.raise_cycles:
            # the unplaced buses are not hoisted at all (their slots stay); the lower instances rise to the maximum
            keep |= {(u["type"], u["bus"]) for u in unplaced}
        if keep:
            pads2 = {tn: {q: {b: v for b, v in bs.items() if (tn, b) not in keep} for q, bs in d.items()}
                     for tn, d in pads.items()}
            hoists, lanes, rest = solve(plan, pads2)
            assert not rest, rest
            rep.update(hoists=[dict(type=t, slot=s, add=k) for (t, s), k in sorted(hoists.items())], lanes=lanes)
            gone = [dict(type=t, bus=b, lane=None, left=1, below=False, target=0, part=None, pad=None) for t, b in keep]
            rep["raised_cycles"] = raise_cycles(plan, pads, gone)
            print(f"  raise-cycles: {len(rep['raised_cycles'])} lanes +{sum(r['add'] for r in rep['raised_cycles'])}"
                  f" cycles on {len(keep)} buses")
            unplaced = []
        if unplaced and not a.partial:
            return 3
        try:
            rep["stale_table_rows"] = apply(plan, hoists)
            rep["resited"] = resite_slots(plan, set(hoists), snap=not a.no_snap)
            break
        except CutError as e:
            lid = e.args[0]
            if not a.raise_cycles or lid not in lanes:
                print(f"pad_hoist: lane {lid}: the hoist would cut fixed cycles below its kit stations")
                return 3
            k = (lanes[lid]["type"], lanes[lid]["bus"])
            if k in keep:
                print(f"pad_hoist: lane {lid} ({k}) still cut after leveling its bus up: refusing")
                return 3
            print(f"  cut below kit stations on {lid}: level {k} up instead")
            keep.add(k)
            unplaced = []
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    Path(a.out_plan).write_text(json.dumps(plan, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
