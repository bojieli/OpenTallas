#!/usr/bin/env python3
"""PATH-HBM-R13 (COORD R13 lane, answer to R12 census finding): opt-in MULTICAST- and DIRECTION-AWARE hub lane model.
A plan that is not passed through it is unchanged (new file; hbm_r10/r11 untouched -- this module swaps
hbm_r10_delta.resolve_lanes for the duration of one run() call only and restores it).

R10/R11 lane transport delivered every core face pin ONCE from one bus of its (direction-blind) core_conns lane group.
The die census (hbm_r18h5) shows hub output ports MULTICAST to >= 2 partitions (pgp.command -> 4 SU groups, xq
xw_data -> 2, svg sm_packet -> 2 SMs ...): ~21k copy bits per hub were left as 'unused bus bits'.  R13:

  1 DIRECTION    every hard-core pin gets its RTL port direction (r18h5 bind bundle RTL + rtl/hbm_accel; generated
                 split cores fall back to the base module); an output pin may only feed out-buses, an input pin only
                 in-buses.  Pins whose module/port is not found keep the R10 direction-blind group (reported).
  2 COVER        R10 regret transport (each pin's bits once) restricted to the direction-legal buses.
  3 MULTICAST    every out-bus still short of its width is filled from its direction-legal output pins (cheapest
                 first, a pin at most its width per bus).  The copy slice is a station of the SAME source net
                 (launch = core pin, from = core pin point) as the pin's other slices, so the per-sink cut counts ONE
                 bundle per cut line (the widest slice crossing it): one bundle per direction that branches toward the
                 landed face crossings, not N copies end-to-end.  --mcast-separate reproduces the R12 upper bound
                 (each copy its own net from the face).
  4 IN SURPLUS   in-bus bits still without a sink after 2 (no legal input pin left) are wired to their cheapest legal
                 input pin as fan-out of the face net (reported 'in_surplus_bits'; upper bound, census owner to rule).
  5 SOFT GLUE    buses with no hard-core pin at all (census soft hub glue, e.g. L42_o/L43_o/L65_o/L73_o) are wired
                 from the face to the nearest hc-root hard core (module contains 'hc_subtree'), reported.
Then hbm_r11_delta.run (y-demand segments, common height, spread pins, option (a), die growth) runs unchanged.
All numbers are plan arithmetic: UNCHECKED until NUMBER-CHECK (12.9f).
"""
import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r10_delta as R10  # noqa: E402
import hbm_r11_delta as R11  # noqa: E402
import hbm_r9_delta as R9  # noqa: E402
import hub_repack as HR  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RTL_ROOTS = ("physical/die_plan/hbm/bind/r18h5_bundle/rtl", "rtl/hbm_accel")
_DECL = re.compile(r"\b(input|output|inout)\b([^;()]*?)(?=[;)]|\b(?:input|output|inout)\b)", re.S)


def module_ports(body):
    body = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", body), flags=re.S)
    out = {}
    for m in _DECL.finditer(body):
        rest = re.sub(r"\[[^\]]*\]", " ", m.group(2))
        rest = re.sub(r"\b(wire|reg|logic|signed|unsigned|var|bit)\b", " ", rest)
        for tok in rest.split(","):
            mm = re.match(r"^\s*([A-Za-z_]\w*)", tok.split("=")[0])
            if mm:
                out.setdefault(mm.group(1), m.group(1))
    return out


def port_dirs(mods, roots=None):
    """{module: {port: input|output|inout}} for the requested modules (split '__x' modules -> base module)."""
    want = set(mods) | {m.split("__")[0] for m in mods}
    src = {}
    for root in roots or [REPO / r for r in RTL_ROOTS]:
        for dp, _, fs in os.walk(root):
            for f in sorted(fs):
                if not f.endswith((".sv", ".v")):
                    continue
                txt = open(os.path.join(dp, f), errors="replace").read()
                for m in re.finditer(r"\bmodule\s+(\w+)", txt):
                    n = m.group(1)
                    if n in want and n not in src:
                        e = txt.find("endmodule", m.start())
                        src[n] = module_ports(txt[m.start():e if e > 0 else None])
    return {m: src.get(m, src.get(m.split("__")[0])) for m in mods}


def resolve_lanes_mcast(t, bi, conns=None, log=print, dirs=None, separate=False, faces=None):
    """drop-in for hbm_r10_delta.resolve_lanes (same return shape)."""
    W, H = t["outline_um"]
    hc = {h["inst"]: h for h in t["hard_cores"]}
    rect = {i: HR._core_rect(h) for i, h in hc.items()}
    bus = {b["name"]: (int(b["width"]), b.get("dir")) for b in t.get("buses", [])}
    keep, pins, tmpl = [], {}, {}
    rep = collections.Counter()
    for s in t["internal_stations"]:
        fa, fb = R10.face_of(s["from_um"], W, H), R10.face_of(s["to_um"], W, H)
        b = s["conn"].split(":", 1)[1] if s["conn"].startswith("bus:") else None
        if b is None or bool(fa) == bool(fb):
            keep.append(s)
            continue
        fend, cend = ("from", "to") if fa else ("to", "from")
        cp = s[cend + "_um"]
        inst = R10._on(rect, cp)
        if inst is None:
            keep.append(s)
            rep["face_to_soft_kept_bits"] += s["bits"]
            continue
        pname = s["capture"] if fend == "from" else s["launch"]
        key = (pname, tuple(cp))
        pin = pins.setdefault(key, dict(bits=0, x=cp[0], y=cp[1], inst=inst, buses={}, dir=None))
        pin["bits"] = max(pin["bits"], int(s["bits"]))
        pin["buses"][b] = fa or fb
        tmpl[(key, b)] = (s, fend)
        rep[f"old_face_bits_{fa or fb}"] += s["bits"]
    # 1 direction
    for key, pin in pins.items():
        d = None
        pn = str(key[0])
        if dirs is not None and "." in pn:
            inst, port = pn.split(".", 1)
            pd = dirs.get(hc[inst]["module"]) if inst in hc else None
            d = (pd or {}).get(port)
        pin["dir"] = {"output": "out", "input": "in"}.get(d)
        legal = [b for b in pin["buses"] if pin["dir"] and bus.get(b, (0, None))[1] == pin["dir"]]
        if pin["dir"] is None:
            rep["dir_unknown_pin_bits"] += pin["bits"]
            pin["legal"] = list(pin["buses"])
        elif not legal:
            rep["dir_no_legal_bus_pin_bits"] += pin["bits"]
            pin["legal"] = list(pin["buses"])
        else:
            rep[f"dir_{pin['dir']}_pin_bits"] += pin["bits"]
            pin["legal"] = legal
    supply = {}
    for pin in pins.values():
        for b in pin["legal"]:
            supply.setdefault(b, bus.get(b, (max(p["bits"] for p in pins.values()), None))[0])

    def cost(pin, b):
        f = pin["buses"][b]
        iv = bi.get(b, {})
        if f in "NS":
            a, c = iv.get("ivx") or (0.0, W)
            return max(0.0, a - pin["x"], pin["x"] - c)
        d = pin["x"] if f == "W" else W - pin["x"]
        a, c = iv.get("ivy") or (0.0, H)
        return d + max(0.0, a - pin["y"], pin["y"] - c)
    # 2 cover (R10 regret order, legal buses only)
    order = []
    for key, pin in pins.items():
        cs = sorted(cost(pin, b) for b in pin["legal"])
        order.append((-(cs[1] - cs[0]) if len(cs) > 1 else -1e18, -pin["bits"], key))
    order.sort()
    rem = dict(supply)
    flows = collections.defaultdict(int)
    kind = {}
    bcast = 0
    for _, _, key in order:
        pin = pins[key]
        need = pin["bits"]
        bl = sorted(pin["legal"], key=lambda b: (cost(pin, b), b))
        for b in bl:
            take = min(need, rem[b])
            if take > 0:
                flows[(key, b)] += take
                kind[(key, b)] = "cover"
                rem[b] -= take
                need -= take
            if need == 0:
                break
        if need > 0:
            flows[(key, bl[0])] += need
            kind.setdefault((key, bl[0]), "cover")
            bcast += need
    rep["cover_unused_out_bits"] = sum(v for b, v in rem.items() if bus.get(b, (0, None))[1] == "out")
    rep["cover_unused_in_bits"] = sum(v for b, v in rem.items() if bus.get(b, (0, None))[1] != "out")
    # 3 multicast (out) / 4 in surplus
    cands = collections.defaultdict(list)
    for key, pin in pins.items():
        for b in pin["legal"]:
            cands[b].append(key)
    for b in sorted(rem):
        if rem[b] <= 0:
            continue
        isout = bus.get(b, (0, None))[1] == "out"
        for key in sorted(cands[b], key=lambda k: (cost(pins[k], b), str(k[0]))):
            room = pins[key]["bits"] - flows.get((key, b), 0)
            take = min(rem[b], room)
            if take <= 0:
                continue
            flows[(key, b)] += take
            kind.setdefault((key, b), "mcast" if isout else "in_surplus")
            rep["mcast_bits" if isout else "in_surplus_bits"] += take
            rem[b] -= take
            if rem[b] <= 0:
                break
    new = []
    assigned = collections.Counter()
    for (key, b), f in flows.items():
        assigned[b] += f
    for (key, b), f in sorted(flows.items(), key=lambda kv: (kv[0][1], str(kv[0][0]))):
        s0, fend = tmpl[(key, b)]
        s = dict(s0, bits=int(f))
        s["regs_um"] = list(s0.get("regs_um", []))
        k = kind.get((key, b), "cover")
        if k == "mcast" and separate:
            s["launch"] = f"face bus {b} mcast"          # R12 upper bound: own net per copy
        if k != "cover":
            s["r13"] = k
        s["r10"] = dict(face=pins[key]["buses"][b], fend=fend, bus=b,
                        ivx=list(bi.get(b, {}).get("ivx") or (0.0, W)),
                        ivy=list(bi.get(b, {}).get("ivy") or (0.0, H)),
                        pin_frac=min(1.0, supply[b] / assigned[b]), bcast=assigned[b] > supply[b])
        new.append(s)
        rep[f"new_face_bits_{s['r10']['face']}"] += f
    # 5 soft glue buses (no hard-core pin)
    hcr = [h for h in t["hard_cores"] if "hc_subtree" in h["module"]]
    pinned = {b for p in pins.values() for b in p["buses"]}
    for bd in t.get("buses", []):
        b = bd["name"]
        if b in pinned or not hcr or b not in bi:
            continue
        f = (faces or {}).get(b)
        if f is None:
            continue
        iv = bi[b]
        if f in "NS":
            x = sum(iv["ivx"]) / 2 if iv.get("ivx") else W / 2
            fp = [x, H if f == "N" else 0.0]
        else:
            y = sum(iv["ivy"]) / 2 if iv.get("ivy") else H / 2
            fp = [0.0 if f == "W" else W, y]
        h = min(hcr, key=lambda h: abs(h["origin_um"][0] + h["outline_um"][0] / 2 - fp[0])
                + abs(h["origin_um"][1] + h["outline_um"][1] / 2 - fp[1]))
        cx = min(max(fp[0], h["origin_um"][0]), h["origin_um"][0] + h["outline_um"][0])
        cy = min(max(fp[1], h["origin_um"][1]), h["origin_um"][1] + h["outline_um"][1])
        out = bd.get("dir") == "out"
        s = dict(conn="bus:" + b, bits=int(bd["width"]), regs_um=[], note="PATH-HBM-R13 soft hub glue (hc root)",
                 launch=(h["inst"] + ".glue") if out else f"face bus {b}", capture=f"face bus {b}" if out else h["inst"],
                 from_um=[cx, cy] if out else fp, to_um=fp if out else [cx, cy], r13="soft_glue")
        s["r10"] = dict(face=f, fend="to" if out else "from", bus=b, ivx=list(iv.get("ivx") or (0.0, W)),
                        ivy=list(iv.get("ivy") or (0.0, H)), pin_frac=1.0, bcast=False)
        new.append(s)
        rep["soft_glue_bits"] += int(bd["width"])
    rep.update(core_pins=len(pins), core_pin_bits=sum(p["bits"] for p in pins.values()),
               bus_supply_bits=sum(supply.values()), unused_bus_bits=sum(max(0, v) for v in rem.values()),
               broadcast_bits=bcast, lane_slices=len(new), old_face_stations=len(tmpl), mcast_separate=separate)
    return keep + new, dict(rep)


def bus_faces(P, part):
    """bus -> hub face from the partner partition geometry (buses carry no face of their own)."""
    T = P["partition_types"]
    pos = {p["name"]: p for p in P["partitions"]}
    hp = pos[part]
    W, H = T[hp["type"]]["outline_um"]
    hx0, hy0 = hp["origin_um"]
    mir = hp.get("orient") == "MY"
    out = {}
    for pt in P["ports"]:
        for side, oth in (("src", "dst"), ("dst", "src")):
            if pt[side]["part"] != part or pt[oth]["part"] not in pos:
                continue
            q = pos[pt[oth]["part"]]
            w, h = T[q["type"]]["outline_um"]
            x0, y0 = q["origin_um"]
            if y0 >= hy0 + H - 1e-3:
                f = "N"
            elif y0 + h <= hy0 + 1e-3:
                f = "S"
            elif x0 + w <= hx0 + 1e-3:
                f = "E" if mir else "W"
            elif x0 >= hx0 + W - 1e-3:
                f = "W" if mir else "E"
            else:
                continue
            out[pt[side]["bus"]] = f
    return out


# ------------------------------------------------------------------ R13 structural options (GEOM-REVIEW-10 conds, price)
def face_affine(Q, W):
    """W/E face stations of a replicated module land on the copy of the face-end segment (W -> 0, E -> S-1) with
    the full width, instead of being split over every copy by N/S lane share (R9): the far copy no longer needs a
    hub-wide leg to the face (R12 price driver: L4/L96 hub<->hub, L51/L101/L126 io<->hub).  Returns moved bits."""
    S = Q["S"]
    out, moved, groups = [], 0, collections.OrderedDict()
    for t in Q["stations"]:
        s = t[0]
        if "r9_share" not in s:
            out.append(t)
            continue
        groups.setdefault(s.get("_r13_id", id(s)), []).append(t)
    for key, L in groups.items():
        s0 = L[0][0]
        orig = int(s0.get("_r13_bits", sum(t[0]["bits"] for t in L)))
        ss, ea, eb, ka, kb = L[0]
        ra = ea[0] == "C" and ea[1].rsplit("__q", 1)[-1].isdigit() and eb[0] == "F"
        fe = eb if ra else ea
        fk = 0 if fe[2][0] <= W / 2 else S - 1
        ce = ea if ra else eb
        name = ce[1].rsplit("__q", 1)[0] + f"__q{fk}"
        ce2 = ("C", name, ce[2])
        s2 = dict(ss, bits=orig, r9_share=1.0, r13_face_affine=True)
        out.append((s2, ce2, fe, fk, fk) if ra else (s2, fe, ce2, fk, fk))
        moved += sum(t[0]["bits"] for t in L if t[3] != fk or t[4] != fk)
    Q["stations"] = out
    return moved


def affinity(Q, t, iters=4, damp=0.5):
    """desired core centres = damped bit-weighted centroid of their station partners (cores + face points), clamped
    into the core's own segment; realise() packs to these centres (topology from them).  Returns mean shift um."""
    W, H = t["outline_um"]
    S = Q["S"]
    bnd = Q.get("bounds") or [Q["seg_w"] * k for k in range(1, S)]
    edges = [0.0] + list(bnd) + [W]
    by = {h["inst"]: h for h in Q["cores"]}
    cen = {n: [h["origin_um"][0] + h["outline_um"][0] / 2, h["origin_um"][1] + h["outline_um"][1] / 2]
           for n, h in by.items()}
    nb = collections.defaultdict(list)
    for s, ea, eb, ka, kb in Q["stations"]:
        b = s.get("bits_parallel", s["bits"])
        for me, ot in ((ea, eb), (eb, ea)):
            if me[0] == "C" and me[1] in by:
                nb[me[1]].append((ot, b))
    tot = 0.0
    c0 = {n: list(v) for n, v in cen.items()}
    for _ in range(iters):
        new = {}
        for n, L in nb.items():
            sx = sy = sw = 0.0
            for ot, b in L:
                if ot[0] == "C":
                    if ot[1] not in cen or ot[1] == n:
                        continue
                    px, py = cen[ot[1]]
                else:
                    px, py = ot[2]
                sx += b * px
                sy += b * py
                sw += b
            if sw <= 0:
                continue
            k = Q["segof"][n]
            w, h = by[n]["outline_um"]
            x = (1 - damp) * cen[n][0] + damp * sx / sw
            y = (1 - damp) * cen[n][1] + damp * sy / sw
            x = min(max(x, edges[k] + w / 2), max(edges[k + 1] - w / 2, edges[k] + w / 2))
            y = min(max(y, h / 2), max(H - h / 2, h / 2))
            new[n] = [x, y]
        cen.update(new)
    cores = []
    for h in Q["cores"]:
        h = dict(h)
        x, y = cen[h["inst"]]
        h["origin_um"] = [x - h["outline_um"][0] / 2, y - h["outline_um"][1] / 2]
        tot += abs(x - c0[h["inst"]][0]) + abs(y - c0[h["inst"]][1])
        cores.append(h)
    Q["cores"] = cores
    return tot / max(len(cores), 1)


def joint_face_pins(stations, W, H, cap=6.0):
    """N/S face pins, span model (a face point of b bits spans b/cap um): the partner-interval groups stay as the
    R10/R11 legaliser put them; pins of buses WITHOUT a partner interval (whole-face groups, r10 ivx = the full
    face) are re-placed into the free face length nearest their consumer, so they no longer stack on the partner
    groups.  Returns (moved points, residual peak pins/um per face, 4-um smoothed like pin_span)."""
    import numpy as np
    pts = collections.OrderedDict()
    for n, s in enumerate(stations):
        r = s.get("r10")
        if not r or r["face"] not in "NS":
            continue
        fe = r["fend"] + "_um"
        key = (r["face"], round(s[fe][0], 3))
        e = pts.setdefault(key, dict(bits=0, flex=True, idx=[]))
        e["bits"] = max(e["bits"], s.get("bits_parallel", s["bits"]))
        if r["ivx"][0] > 0.5 or r["ivx"][1] < W - 0.5:
            e["flex"] = False
        e["idx"].append((n, fe))
    # other face points (non-r10 stations on the N/S faces) are fixed occupancy too
    other = collections.defaultdict(int)
    for s in stations:
        if s.get("r10"):
            continue
        for p in (s["from_um"], s["to_um"]):
            if p[1] <= 0.5 or p[1] >= H - 0.5:
                k = ("S" if p[1] <= 0.5 else "N", round(p[0], 3))
                other[k] = max(other[k], s.get("bits_parallel", s["bits"]))
    n_um = int(W) + 2
    occ = {f: np.zeros(n_um) for f in "NS"}

    def lay(f, x, b, sign=1.0):
        a, c = x - b / cap / 2, x + b / cap / 2
        occ[f][max(0, int(np.floor(a))):min(n_um, int(np.ceil(c)))] += sign * cap
    for (f, x), e in pts.items():
        if not e["flex"]:
            lay(f, x, e["bits"])
    for (f, x), b in other.items():
        lay(f, x, b)
    moved = 0
    flex = sorted(((k, e) for k, e in pts.items() if e["flex"]), key=lambda kv: -kv[1]["bits"])
    for (f, x), e in flex:
        L = max(1, int(np.ceil(e["bits"] / cap)))
        free = occ[f] + cap <= cap + 1e-9            # um with no pin yet
        # windows of L free um: start positions
        c = np.concatenate([[0], np.cumsum(free.astype(int))])
        ok = np.nonzero(c[L:] - c[:-L] == L)[0] if L < n_um else np.array([], dtype=int)
        if ok.size == 0:
            lay(f, x, e["bits"])
            continue
        centres = ok + L / 2
        j = int(np.argmin(np.abs(centres - x)))
        nx = round(float(min(max(centres[j], 0.0), W)), 3)
        lay(f, nx, e["bits"])
        if abs(nx - x) > 1e-6:
            moved += 1
            for n, fe in e["idx"]:
                stations[n][fe] = [nx, stations[n][fe][1]]
    peak = {f: round(float(np.convolve(occ[f], np.ones(4) / 4, "same").max()), 3) for f in "NS"}
    return moved, peak


def r3_(v):
    return round(v, 3)


def run(plan_dir, out_dir, hubs, separate=False, dirs=None, affine=False, aff_iters=0, joint_pins=False, **kw):
    P = json.loads((Path(plan_dir) / "die_plan.json").read_text())
    if dirs is None:
        mods = {h["module"] for _, tn in hubs for h in P["partition_types"][tn]["hard_cores"]}
        dirs = port_dirs(mods)
    sig = lambda t: json.dumps([t["outline_um"], t["internal_stations"][:3], len(t["internal_stations"])])  # noqa: E731
    byt = {sig(P["partition_types"][tn]): bus_faces(P, part) for part, tn in hubs}
    orig = R10.resolve_lanes

    def _res(t, bi, conns=None, log=print):
        return resolve_lanes_mcast(t, bi, conns, log, dirs, separate, byt.get(sig(t), {}))
    R10.resolve_lanes = _res
    opq, osp = R9.plan_quadrants, R11.spread_place
    stat = collections.defaultdict(list)

    def _pq(t, S, *a, **k):
        for n, s in enumerate(t["internal_stations"]):
            s["_r13_bits"], s["_r13_id"] = s["bits"], n
        Q = opq(t, S, *a, **k)
        for s in t["internal_stations"]:
            s.pop("_r13_bits", None)
            s.pop("_r13_id", None)
        if affine:
            Q["r13_face_affine_moved_bits"] = face_affine(Q, t["outline_um"][0])
        if aff_iters:
            Q["r13_affinity_mean_shift_um"] = affinity(Q, t, aff_iters)
        for x in Q["stations"]:
            x[0].pop("_r13_bits", None)
            x[0].pop("_r13_id", None)
        return Q

    def _sp(st, W, H, cap, spread):
        d = osp(st, W, H, cap, spread)
        if joint_pins:
            stat["joint_pins"].append(joint_face_pins(st, W, H, cap))
        return d
    R9.plan_quadrants, R11.spread_place = _pq, _sp
    try:
        rep = R11.run(plan_dir, out_dir, hubs, **kw)
    finally:
        R10.resolve_lanes = orig
        R9.plan_quadrants, R11.spread_place = opq, osp
    rep["r13"] = dict(multicast=True, direction=True, separate=separate, face_affine=affine, affinity_iters=aff_iters,
                      joint_pins=joint_pins, joint_pins_last=stat["joint_pins"][-4:],
                      modules_without_rtl=sorted(m for m, v in dirs.items() if v is None))
    (Path(out_dir) / "r13_delta_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hubs", default="NW_hub:q_hub_nw,NE_hub:q_hub_ne")
    ap.add_argument("--mcast-separate", action="store_true", help="R12 upper bound: each copy its own net")
    ap.add_argument("--face-affine", action="store_true", help="W/E face legs -> face-end segment copy")
    ap.add_argument("--affinity-iters", type=int, default=0, help="affinity re-place iterations (0 = R9 positions)")
    ap.add_argument("--joint-face-pins", action="store_true", help="N/S face pins <= --pins-per-um per gcell")
    ap.add_argument("--height-um", type=float, default=None)
    ap.add_argument("--bound-um", action="append", default=[])
    ap.add_argument("--pins-per-um", type=float, default=6.0)
    ap.add_argument("--spread-pins-per-um", type=float, default=3.0)
    ap.add_argument("--cc-serial-k", type=int, default=1)
    ap.add_argument("--cc-min-um", type=float, default=1000.0)
    ap.add_argument("--k-max", type=int, default=8)
    ap.add_argument("--grow-die", action="store_true")
    ap.add_argument("--grow-row-types", action="store_true")
    ap.add_argument("--no-route", action="store_true")
    ap.add_argument("--jobs", type=int, default=36)
    a = ap.parse_args(argv)
    hubs = [tuple(x.split(":")) for x in a.hubs.split(",") if x]
    bounds = {b.split(":")[0]: float(b.split(":")[1]) for b in a.bound_um}
    rep = run(a.plan_dir, a.out, hubs, separate=a.mcast_separate, affine=a.face_affine, aff_iters=a.affinity_iters,
              joint_pins=a.joint_face_pins, height=a.height_um, bounds=bounds or None,
              cap=a.pins_per_um, spread=a.spread_pins_per_um, kcc=a.cc_serial_k, cc_min=a.cc_min_um, kmax=a.k_max,
              route=not a.no_route, grow=a.grow_die, grow_row=a.grow_row_types, jobs=a.jobs)
    for tn, r in rep["hubs"].items():
        c = r["cut_per_sink_blocked"]
        ln = r["lanes"]
        print(f"{tn}: b {r['bound_um']} H {r['height_um']} k {r['k']} cut x {c['x']['max_use']} y {c['y']['max_use']} "
              f"segments {[(s['cut_x'], s['cut_y']) for s in r['segments']]} cc_serialised {r['cc_serialised']} "
              f"mcast {ln.get('mcast_bits', 0)} in_surplus {ln.get('in_surplus_bits', 0)} soft_glue "
              f"{ln.get('soft_glue_bits', 0)} unused {ln.get('unused_bus_bits')} dir_unknown {ln.get('dir_unknown_pin_bits', 0)}")
    print("die_growth_um", rep["die_growth_um"], "plan_sha256", rep["plan_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
