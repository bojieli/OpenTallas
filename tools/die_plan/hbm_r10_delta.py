#!/usr/bin/env python3
"""PATH-HBM-R10 (COORD 16:13 RULING PATH-HBM-R9): opt-in HBM hub delta -- TOP-DOWN LANE ENTRY.
A plan that is not passed through it is unchanged (new file; hbm_r9_delta only gains opt-in keyword arguments).

The R6..R9 hub internal_stations carry the census CROSS-PRODUCT of core_conns.json: every core face pin is tied
to every face bus of its lane group (3-28 buses per pin), each station with the FULL pin width.  On q_hub_nw that is
545k face station bits for 631 distinct core pins (73.7k bits) and 87 face buses (86.9k bits).  R10 replaces it, at
plan time, with ONE top-down lane -> pin assignment (owner 10-13 top-down pin rule, new/unclosed tile):

  1 LANE TRANSPORT  every face bus delivers at most its width; every core face pin receives its bits once, from the
                    buses core_conns allows for it (lane <-> identical-instance swap is implicit: which pc_ctrl /
                    vms_bank / ... instance a lane slice lands on is chosen by position).  Greedy regret transport,
                    cost = x distance between the pin and the bus partner's abutment interval (N/S) / face (W/E).
                    Pin demand that the allowed buses cannot supply is kept as a broadcast (reported, not dropped).
  2 PIN PLACEMENT   every lane slice gets its own face pin span placed over its consumer pin: N/S x = consumer x
                    clamped into the abutment interval of the partner partition (die-level lane unchanged; the
                    partner moves its matching pin along the same shared edge), W/E y into the port window; 1-D
                    legalised at --pins-per-um (plan budget face_pins_per_um, default 6).
  3 SEGMENTS        (S >= 2) hbm_r9_delta service quadrants with boundaries at EQUAL N/S LANE BITS (4.32 snapped),
                    distributed instances start in the segment of their own x (their lanes follow them).  Pins are
                    re-placed over the packed consumers.
  4 W/E CHAIN       W/E face lane slices whose consumer is more than one hop (--hop-um 405) from the edge ride a
                    registered serialised neighbour chain: ceil(bits/k) beats, serialiser at the face pin register,
                    k-deep deserialiser at the consumer pin, one register per segment boundary (static schedule, no
                    credits).  Inter-segment links serialised by the same k (r9 kx).
  k = smallest of 1..8 with plan_cut per-sink (blocked) <= 0.6 on every cut, else 8.
Writes <out>/die_plan.json (+ r10_delta_report.json); everything else hard-linked.  The die outline is NOT changed
(type outline only; die growth reported).  All numbers are plan arithmetic: UNCHECKED until NUMBER-CHECK (12.9f).
"""
import argparse
import bisect
import collections
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r9_delta as R9  # noqa: E402
import hub_repack as HR  # noqa: E402
import plan_cut as PC  # noqa: E402

r3 = HR.r3


def face_of(p, W, H, tol=0.5):
    if p[1] <= tol:
        return "S"
    if p[1] >= H - tol:
        return "N"
    if p[0] <= tol:
        return "W"
    if p[0] >= W - tol:
        return "E"
    return None


def bus_intervals(P, part, t):
    """bus -> dict(partner, iv) : iv = abutment interval of the partner on the hub face, in hub-type x (N/S) or
    the port window in hub-type y (W/E); None when the plan does not say."""
    T = P["partition_types"]
    pos = {p["name"]: p for p in P["partitions"]}
    hp = pos[part]
    W, H = t["outline_um"]
    ox, oy = hp["origin_um"]
    mir = hp.get("orient") == "MY"
    out = {}
    for pt in P["ports"]:
        for side, oth in (("src", "dst"), ("dst", "src")):
            if pt[side]["part"] != part:
                continue
            pr = pos.get(pt[oth]["part"])
            ivx = ivy = None
            if pr:
                w = T[pr["type"]]["outline_um"][0]
                a, b = pr["origin_um"][0] - ox, pr["origin_um"][0] + w - ox
                if mir:
                    a, b = W - b, W - a
                ivx = (max(0.0, a), min(W, b)) if min(W, b) > max(0.0, a) else None
            if pt.get("window_um"):
                ivy = (pt["window_um"][0] - oy, pt["window_um"][1] - oy)
            out[pt[side]["bus"]] = dict(partner=pt[oth]["part"], ivx=ivx, ivy=ivy)
    return out


def _on(rect, p, tol=0.5):
    return R9._on(rect, p, tol)


def legalise(items, lo, hi, cap):
    """1-D clumping legaliser: items [(key, desired, bits)] -> {key: centre}; span bits/cap each inside [lo, hi]
    (scaled down when the interval is over capacity: density reported)."""
    if not items:
        return {}, 0.0
    L = hi - lo
    need = sum(b for _, _, b in items) / cap
    sc = min(1.0, L / need) if need > 0 else 1.0
    its = sorted(((d, k, b / cap * sc) for k, d, b in items), key=lambda x: (x[0], str(x[1])))
    clusters = []          # [start, width, sum_w*d, sum_w, members]
    for d, k, w in its:
        c = [d - w / 2, w, (d - w / 2) * max(w, 1e-9), max(w, 1e-9), [(k, w)]]
        clusters.append(c)
        while True:
            c = clusters[-1]
            c[0] = min(max(c[2] / c[3], lo), hi - c[1])
            if len(clusters) > 1 and clusters[-2][0] + clusters[-2][1] > c[0] + 1e-9:
                p = clusters[-2]
                off = p[1]
                p[2] += c[2] - off * c[3]
                p[3] += c[3]
                p[1] += c[1]
                p[4] += c[4]
                clusters.pop()
                continue
            break
    out = {}
    for c in clusters:
        x = c[0]
        for k, w in c[4]:
            out[k] = r3(x + w / 2)
            x += w
    return out, (need / L if L > 0 else float("inf"))


def resolve_lanes(t, bi, conns=None, log=print):
    """steps 1-2 on one hub type (in place on a copy of its stations). Returns (stations, report)."""
    W, H = t["outline_um"]
    hc = {h["inst"]: h for h in t["hard_cores"]}
    rect = {i: HR._core_rect(h) for i, h in hc.items()}
    width = {b["name"]: int(b["width"]) for b in t.get("buses", [])}
    keep, pins, tmpl = [], {}, {}
    rep = collections.Counter()
    for s in t["internal_stations"]:
        fa, fb = face_of(s["from_um"], W, H), face_of(s["to_um"], W, H)
        bus = s["conn"].split(":", 1)[1] if s["conn"].startswith("bus:") else None
        if bus is None or bool(fa) == bool(fb):
            keep.append(s)
            continue
        fend, cend = ("from", "to") if fa else ("to", "from")
        cp = s[cend + "_um"]
        inst = _on(rect, cp)
        if inst is None:
            keep.append(s)
            rep["face_to_soft_kept_bits"] += s["bits"]
            continue
        pname = s["capture"] if fend == "from" else s["launch"]
        key = (pname, tuple(cp))
        f = fa or fb
        pin = pins.setdefault(key, dict(bits=0, x=cp[0], y=cp[1], inst=inst, buses={}))
        pin["bits"] = max(pin["bits"], int(s["bits"]))
        pin["buses"][bus] = f
        tmpl[(key, bus)] = (s, fend)
        rep[f"old_face_bits_{f}"] += s["bits"]
    supply = {}
    for key, pin in pins.items():
        for bus in pin["buses"]:
            supply.setdefault(bus, width.get(bus, max(p["bits"] for p in pins.values())))

    def cost(pin, bus):
        f = pin["buses"][bus]
        iv = bi.get(bus, {})
        if f in "NS":
            a, b = iv.get("ivx") or (0.0, W)
            return max(0.0, a - pin["x"], pin["x"] - b)
        d = pin["x"] if f == "W" else W - pin["x"]
        a, b = iv.get("ivy") or (0.0, H)
        return d + max(0.0, a - pin["y"], pin["y"] - b)
    order = []
    for key, pin in pins.items():
        cs = sorted(cost(pin, b) for b in pin["buses"])
        order.append((-(cs[1] - cs[0]) if len(cs) > 1 else -1e18, -pin["bits"], key))
    order.sort()
    rem = dict(supply)
    flows = collections.defaultdict(int)
    bcast = 0
    for _, _, key in order:
        pin = pins[key]
        need = pin["bits"]
        bl = sorted(pin["buses"], key=lambda b: (cost(pin, b), b))
        for b in bl:
            take = min(need, rem[b])
            if take > 0:
                flows[(key, b)] += take
                rem[b] -= take
                need -= take
            if need == 0:
                break
        if need > 0:
            flows[(key, bl[0])] += need
            bcast += need
    new = []
    assigned = collections.Counter()
    for (key, bus), f in flows.items():
        assigned[bus] += f
    for (key, bus), f in sorted(flows.items(), key=lambda kv: (kv[0][1], str(kv[0][0]))):
        s0, fend = tmpl[(key, bus)]
        s = dict(s0, bits=int(f))
        s["regs_um"] = list(s0.get("regs_um", []))
        s["r10"] = dict(face=pins[key]["buses"][bus], fend=fend, bus=bus,
                        ivx=list(bi.get(bus, {}).get("ivx") or (0.0, W)),
                        ivy=list(bi.get(bus, {}).get("ivy") or (0.0, H)),
                        pin_frac=min(1.0, supply[bus] / assigned[bus]), bcast=assigned[bus] > supply[bus])
        new.append(s)
        rep[f"new_face_bits_{s['r10']['face']}"] += f
    rep.update(core_pins=len(pins), core_pin_bits=sum(p["bits"] for p in pins.values()),
               bus_supply_bits=sum(supply.values()), unused_bus_bits=sum(rem.values()), broadcast_bits=bcast,
               lane_slices=len(new), old_face_stations=len(tmpl))
    return keep + new, dict(rep)


def place_pins(stations, W, H, cap, Hscale=1.0):
    """step 2: every r10 lane slice's face pin over its consumer, legalised per (face, interval)."""
    groups = collections.defaultdict(list)
    bc = collections.defaultdict(list)          # over-subscribed (broadcast) bus: ONE pin location, fan-out inside
    for n, s in enumerate(stations):
        r = s.get("r10")
        if r and r.get("bcast"):
            cp = s["to_um" if r["fend"] == "from" else "from_um"]
            bc[r["bus"]].append((cp[0] if r["face"] in "NS" else cp[1], s["bits"]))
    med = {}
    for bus, L in bc.items():
        L.sort()
        tot, acc = sum(b for _, b in L), 0
        for v, b in L:
            acc += b
            if acc >= tot / 2:
                med[bus] = v
                break
    for n, s in enumerate(stations):
        r = s.get("r10")
        if not r:
            continue
        cp = s["to_um" if r["fend"] == "from" else "from_um"]
        pb = s.get("bits_parallel", s["bits"]) * r.get("pin_frac", 1.0)
        if r["face"] in "NS":
            a, b = r["ivx"]
            d = med.get(r["bus"], cp[0]) if r.get("bcast") else cp[0]
        else:
            a, b = r["ivy"][0] * Hscale, r["ivy"][1] * Hscale
            d = med.get(r["bus"], cp[1]) if r.get("bcast") else cp[1]
        groups[(r["face"], a, b)].append((n, min(max(d, a), b), pb))
    dens = 0.0
    for (f, a, b), items in groups.items():
        pos, d = legalise(items, a, b, cap)
        dens = max(dens, d)
        for n, v in pos.items():
            s = stations[n]
            fe = s["r10"]["fend"] + "_um"
            if f == "N":
                s[fe] = [v, H]
            elif f == "S":
                s[fe] = [v, 0.0]
            elif f == "W":
                s[fe] = [0.0, v]
            else:
                s[fe] = [W, v]
    return r3(dens)


def chain_we(stations, W, k, hop=405.0):
    """step 4: W/E lane slices beyond one hop -> serialised neighbour chain (ceil(bits/k))."""
    n = 0
    for s in stations:
        r = s.get("r10")
        if not r or r["face"] not in "WE":
            continue
        cp = s["to_um" if r["fend"] == "from" else "from_um"]
        d = cp[0] if r["face"] == "W" else W - cp[0]
        par = s.get("bits_parallel", s["bits"])
        if k > 1 and d > hop:
            s["bits_parallel"] = par
            s["bits"] = int(math.ceil(par / k))
            s["serial_k"] = k
            s["r10_we_chain"] = True
            n += 1
    return n


def profile(W, H, t_like, x0=0.0, x1=None, lower_pg_frac=0.25):
    """plan_cut per-sink blocked profile restricted to the x band [x0, x1] (nets clipped to it)."""
    x1 = W if x1 is None else x1
    nets = []
    for n in PC._nets(t_like):
        xs = [p[0] for p in n["pts"]]
        if max(xs) < x0 or min(xs) > x1:
            continue
        m = dict(n, pts=[[min(max(p[0], x0), x1) - x0, p[1]] for p in n["pts"]])
        nets.append(m)
    cores = {}
    for i, (a, b, c, d) in PC._cores(t_like).items():
        if c > x0 and a < x1:
            cores[i] = (max(a, x0) - x0, b, min(c, x1) - x0, d)
    return PC._cut_profile(x1 - x0, H, nets, cores, lower_pg_frac=lower_pg_frac, per_sink=True)


def lane_bounds(stations, W, S):
    """S-1 boundaries at equal N/S lane bits (pin x), snapped to the 4.32 lattice."""
    pts = sorted((s[s["r10"]["fend"] + "_um"][0], s["bits"]) for s in stations
                 if s.get("r10") and s["r10"]["face"] in "NS")
    tot = sum(b for _, b in pts)
    out, acc, j = [], 0, 1
    for x, b in pts:
        acc += b
        while j < S and acc >= tot * j / S:
            out.append(HR.sn(x))
            j += 1
    out = sorted(min(max(v, 4.32), W - 4.32) for v in out[:S - 1])
    return out


def run_hub(P, part, tn, S, cap=6.0, kmax=8, hop=405.0, route=True, log=print, bounds_mode="lanes", height=None):
    t = P["partition_types"][tn]
    W, H = t["outline_um"]
    bi = bus_intervals(P, part, t)
    st, lrep = resolve_lanes(t, bi, log=log)
    t1 = dict(t, internal_stations=st)
    dens = place_pins(st, W, H, cap)
    base = R9.cut(dict(outline_um=[W, H], hard_cores=t["hard_cores"], internal_stations=t["internal_stations"]))
    res = dict(lanes=lrep, pin_density_max_over_cap=dens, base_cut_blocked=base["blocked"])
    rows = []
    if S == 1:
        Hn, cores, bounds, infos, Q = H, t["hard_cores"], [], {0: dict(x_um=[0.0, W])}, None
        import copy as _c
        for k in range(1, kmax + 1):
            s2 = _c.deepcopy(st)
            nser = chain_we(s2, W, k, hop)
            u = R9.cut(dict(outline_um=[W, H], hard_cores=cores, internal_stations=s2))
            mu = max(u["blocked"]["x"]["max_use"], u["blocked"]["y"]["max_use"])
            rows.append(dict(k=k, cut_x=u["blocked"]["x"]["max_use"], cut_y=u["blocked"]["y"]["max_use"],
                             we_chain=nser))
            log(f"{tn}: S=1 k {k} cut x {u['blocked']['x']['max_use']} y {u['blocked']['y']['max_use']}")
            if mu <= 0.6 + 1e-9:
                break
        kch = rows[-1]["k"]
        final = _c.deepcopy(st)
        nser = chain_we(final, W, kch, hop)
        stats = dict(stations=len(final), we_chain=nser, serialised=nser)
        if route:
            R = HR.Raster(W, H, [HR._core_rect(h) for h in cores])
            stats.update(_route(R, final, hop))
    else:
        bounds = lane_bounds(st, W, S) if bounds_mode == "lanes" else [r3(HR.sn(W * j / S)) for j in range(1, S)]
        Q = R9.plan_quadrants(t1, S, bounds=bounds, dist_by_x=True)
        Hn = R9.min_height(t1, Q, H, log=log)
        if height is not None:
            if float(height) < Hn:
                raise ValueError(f"--height-um {height} below the packing minimum {Hn}")
            Hn = r3(HR.ce(float(height), 8.64))
        kch = None
        for k in range(1, kmax + 1):
            cores, s2, infos, stats = R9.realise(t1, Q, Hn, kx=k, route=False)
            place_pins(s2, W, Hn, cap, Hscale=Hn / H)
            nser = chain_we(s2, W, k, hop)
            u = R9.cut(dict(outline_um=[W, Hn], hard_cores=cores, internal_stations=s2))
            mu = max(u["blocked"]["x"]["max_use"], u["blocked"]["y"]["max_use"])
            rows.append(dict(k=k, cut_x=u["blocked"]["x"]["max_use"], cut_y=u["blocked"]["y"]["max_use"],
                             we_chain=nser, inter_segment_serialised=stats["serialised"]))
            log(f"{tn}: S={S} H {Hn} k {k} cut x {u['blocked']['x']['max_use']} y {u['blocked']['y']['max_use']}")
            kch = k
            if mu <= 0.6 + 1e-9:
                break
        cores, final, infos, stats = R9.realise(t1, Q, Hn, kx=kch, route=route)
        place_pins(final, W, Hn, cap, Hscale=Hn / H)
        stats["we_chain"] = chain_we(final, W, kch, hop)
    u = R9.cut(dict(outline_um=[W, Hn], hard_cores=cores, internal_stations=final))
    edges = [0.0] + list(bounds) + [W]
    segs = []
    for k in range(len(edges) - 1):
        pr = profile(W, Hn, dict(hard_cores=cores, internal_stations=final), edges[k], edges[k + 1])
        segs.append(dict(x_um=[r3(edges[k]), r3(edges[k + 1])], cut_x=pr["x"].get("max_use"),
                         cut_y=pr["y"].get("max_use"), at_x=pr["x"].get("at_um"), at_y=pr["y"].get("at_um")))
    bb = [0] * max(0, len(edges) - 2)
    for s in final:
        sg = s.get("r9_segments")
        if sg:
            for j in range(min(sg), max(sg)):
                bb[j] += s["bits"]
    res.update(S=S, k=kch, k_table=rows, outline_um_new=[W, Hn], hub_growth_y_um=r3(Hn - H), bounds_um=bounds,
               cut_per_sink=u, segments=segs, boundary_bits_serialised=bb, stations=stats,
               latency_cycles=dict(serialised_transfer_added=(kch - 1) if kch else 0,
                                   note="each serialised lane slice: +k-1 cycles (k beats) and 1/k of its parallel "
                                        "bandwidth; extra station registers in stations.latency_up_hist"))
    return cores, final, Hn, res, Q


def _route(R, stations, reach):
    lat = collections.Counter()
    out = dict(regs_old=0, regs_new=0, latency_up=0, failed=0)
    for s in stations:
        n_old = len(s.get("regs_um", []))
        out["regs_old"] += n_old
        r = HR.route_station(R, s["from_um"], s["to_um"], n_old, 360.0)
        if r is None:
            out["failed"] += 1
            out["regs_new"] += n_old
            continue
        s["regs_um"] = [list(x) for x in r["regs"]]
        out["regs_new"] += len(r["regs"])
        if len(r["regs"]) > n_old:
            out["latency_up"] += 1
            lat[len(r["regs"]) - n_old] += 1
    out["latency_up_hist"] = dict(sorted(lat.items()))
    return out


def run(plan_dir, out_dir, hubs, S=1, cap=6.0, route=True, log=print, bounds_mode="lanes", kmax=8, height=None):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    P = json.loads((plan_dir / "die_plan.json").read_text())
    rep = dict(schema="opentallas.hbm_r10_delta.v1", source_plan_sha256=hashlib.sha256(
        (plan_dir / "die_plan.json").read_bytes()).hexdigest(), segments=S, pins_per_um=cap, hubs={},
        note="plan arithmetic, UNCHECKED until NUMBER-CHECK (12.9f); lane transport is a plan MODEL of the "
             "core_conns cross-product (needs the hub glue bit map to confirm)")
    for part, tn in hubs:
        t = P["partition_types"][tn]
        W, H = t["outline_um"]
        cores, st, Hn, res, Q = run_hub(P, part, tn, S, cap=cap, kmax=kmax, route=route, log=log, bounds_mode=bounds_mode, height=height)
        res["bounds_mode"] = bounds_mode
        for s in st:
            s.pop("r10", None)
        rep["hubs"][tn] = res
        t["outline_um"] = [W, Hn]
        t["hard_cores"] = cores
        t["internal_stations"] = st
        if Q is not None:
            byname = {h["inst"]: h for h in cores}
            t["contents"] = [c for c in t.get("contents", []) if c.get("inst") in byname] + [
                dict(inst=h["inst"], module=h["module"], status="new", cells=None, note=h.get("note", ""),
                     origin_um=list(h["origin_um"]), outline_um=list(h["outline_um"])) for h in cores
                if "__q" in h["inst"]]
            for c in t["contents"]:
                if c.get("inst") in byname:
                    c["origin_um"] = list(byname[c["inst"]]["origin_um"])
        t["note"] = (t.get("note", "") + f" | PATH-HBM-R10 top-down lane entry S={S} k={res['k']}").strip(" |")
    rep["die_growth_um"] = max([0.0] + [v["hub_growth_y_um"] for v in rep["hubs"].values()])
    P["note"] = (P.get("note", "") + f" | PATH-HBM-R10 delta: hubs {[h for _, h in hubs]} lane entry S={S} "
                 f"(type outlines only; die growth {rep['die_growth_um']} um NOT applied)").strip(" |")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    for name in ("die_plan.json", "die_plan.sha256"):
        if (out_dir / name).exists():
            (out_dir / name).unlink()
    (out_dir / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
    sha = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "die_plan.sha256").write_text(f"{sha}  die_plan.json\n")
    rep["plan_sha256"] = sha
    (out_dir / "r10_delta_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hubs", default="NW_hub:q_hub_nw,NE_hub:q_hub_ne")
    ap.add_argument("--segments", type=int, default=1)
    ap.add_argument("--pins-per-um", type=float, default=6.0)
    ap.add_argument("--no-route", action="store_true")
    ap.add_argument("--height-um", type=float, default=None,
                    help="S>=2: hub height (>= packing minimum; area is free per owner 16:50, taller = more x-cut tracks)")
    ap.add_argument("--k-max", type=int, default=8, help="largest serialisation factor tried (W/E chain + inter-segment)")
    ap.add_argument("--bounds", choices=("lanes", "width"), default="lanes",
                    help="segment boundaries at equal N/S lane bits (R10 ruling) or equal widths (comparison)")
    a = ap.parse_args(argv)
    hubs = [tuple(x.split(":")) for x in a.hubs.split(",") if x]
    rep = run(a.plan_dir, a.out, hubs, a.segments, a.pins_per_um, route=not a.no_route, bounds_mode=a.bounds, kmax=a.k_max, height=a.height_um)
    for tn, r in rep["hubs"].items():
        c = r["cut_per_sink"]["blocked"]
        print(f"{tn}: S {r['S']} k {r['k']} H {r['outline_um_new'][1]} cut x {c['x']['max_use']} y {c['y']['max_use']} "
              f"segments {[(s['cut_x'], s['cut_y']) for s in r['segments']]} lanes {r['lanes']}")
    print("die_growth_um", rep["die_growth_um"], "plan_sha256", rep["plan_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
