#!/usr/bin/env python3
"""Feedthrough plan (FT-TOOL, FT-PLAN owner 10-23): lane routes, stage placement, per-block ft spec, stage counts.

    plan.py --die D --census CENSUS.json[.gz] --dump DUMPDIR --out PLANDIR
            [--policy straight|row] [--ft-reg inout|single] [--ft-clock block|forwarded] [--kinds data,ctl]
            [--forbid-re REGEX] [--slot-um S] [--occupancy 0.6] [--max-shift-um 1500] [--reach-um R]

1. ROUTE (greedy, widest x longest first).  Candidates: HV and VH Manhattan L (policy row: HV only = the horizontal
   leg at the source pin row, S81 row-aligned).  A candidate crossing a FORBIDDEN block (hard IP: PHY / SerDes / UCIe
   / HBM PHY by default; they get no ft and no repeaters) is invalid; cost = length + 4 x (sum over crossed faces of
   (load + bits) / (ratio x tracks)) so heavy faces are balanced.  No valid candidate -> keep_channel (the lane stays
   on its current relay route, re-spaced at reach).
2. TRACKS.  Every leg (H on the horizontal ft layer, V on the vertical one) gets a die-frame track band of width
   bits x pitch / occupancy, packed greedily near its natural coordinate (shift <= max_shift; --slot-um snaps bands to
   a corridor grid so block variants quantise).  Because the band is assigned once per leg in the DIE frame, the out
   port of a block and the in port of its abutting neighbour are at the same offset by construction.
3. STAGES.  Along the final route: every crossed block gets a register at its in pin and its out pin (inout; the
   pin-register rule) and internal registers <= reach apart; a channel gap between two registers longer than reach
   gets channel relays (ceil(gap/reach)-1, evenly).  Repeater sites every <= rep_um between registers.
   stages_new = registers strictly between source and sink.
4. SPECS.  One ftspec per hosting block (README "ft spec"), coordinates in the MASTER frame; variant =
   master + hash of the port/path signature, so identical crossings share one hardening.

Outputs: PLANDIR/<die>_plan.json, <die>_schedule.tsv, ftspec/<inst>.json, <die>_plan.png.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import census as census_mod  # noqa: E402
import dies  # noqa: E402
import geom  # noqa: E402
from dump_io import Dump  # noqa: E402

SCHEMA = "opentallas.die_feedthrough.plan.v1"
SPEC_SCHEMA = "opentallas.die_feedthrough.ftspec.v1"
FORBID_RE = r"(phy|serdes|ucie|hbm3e|pll|bump)"
PIN_INSET_UM = 20.0
JOG_MIN_UM = 20.0          # --band-jogs: pin -> band jogs longer than this get their own track band
JOG_SHIFT_UM = 300.0        # in / out register distance from the block face


def inv_xform(X, Y, W, H, orient, x0=0.0, y0=0.0):
    """die point -> master frame point (inverse of geom.xform)."""
    X, Y = X - x0, Y - y0
    o = orient or "R0"
    return {"R0": (X, Y), "R180": (W - X, H - Y), "MX": (X, H - Y), "MY": (W - X, Y), "R90": (Y, H - X),
            "R270": (W - Y, X), "MXR90": (Y, X), "MYR90": (W - Y, H - X)}[o]


def n_tracks(bits, occupancy, ft_clock):
    """tracks of a lane band: data bits (+ the forwarded clock bit) at the occupancy limit."""
    return int(math.ceil((bits + (1 if ft_clock == "forwarded" else 0)) / occupancy - 1e-9))


def load_census(p):
    return json.load(gzip.open(p, "rt") if str(p).endswith(".gz") else open(p))


def ft_layer(dump, layers, horizontal):
    want = "HORIZONTAL" if horizontal else "VERTICAL"
    for ln in layers:
        L = dump.layer(ln)
        if L and L["dir"] == want:
            return ln, L["pitch"]
    return layers[0], 0.08


class Tracks:
    """track-band packing per orientation in the die frame on a numpy occupancy grid:
    grid[horiz][span_bin, track] = used.  A horizontal leg spans x bins and occupies consecutive y tracks (pitch of the
    horizontal ft layer); a band of n = ceil(bits / occupancy) tracks is placed at the free run nearest its natural
    coordinate within max_shift."""

    def __init__(self, die_box, pitch_h, pitch_v, span_bin=250.0):
        import numpy as np
        self.np = np
        x0, y0, x1, y1 = die_box
        self.o = (x0, y0)
        self.sb = span_bin
        self.p = {True: pitch_h, False: pitch_v}
        # horizontal legs: span along x, tracks along y
        self.g = {True: np.zeros((int((x1 - x0) // span_bin) + 1, int((y1 - y0) / pitch_h) + 1), dtype=bool),
                  False: np.zeros((int((y1 - y0) // span_bin) + 1, int((x1 - x0) / pitch_v) + 1), dtype=bool)}

    def place(self, horiz, c0, ntr, a, b, max_shift, slot=0.0):
        """-> (centre coordinate, overflow?)."""
        np = self.np
        g = self.g[horiz]
        p = self.p[horiz]
        so = self.o[0] if horiz else self.o[1]       # span origin
        co = self.o[1] if horiz else self.o[0]       # track origin
        i0 = max(0, int((min(a, b) - so) // self.sb))
        i1 = min(g.shape[0] - 1, int((max(a, b) - so) // self.sb))
        t0 = (c0 - co) / p
        half = int(max_shift / p) + ntr
        lo = max(0, int(t0) - half)
        hi = min(g.shape[1], int(t0) + half + ntr)
        if hi - lo < ntr:
            return c0, True
        blocked = g[i0:i1 + 1, lo:hi].any(axis=0)
        cs = np.concatenate(([0], np.cumsum(~blocked)))
        ok = (cs[ntr:] - cs[:-ntr]) == ntr          # run starting at j (relative to lo) is free
        js = np.nonzero(ok)[0]
        if slot:
            step = max(1, int(round(slot / p)))
            js = js[((js + lo) % step) == 0]
        if len(js) == 0:
            j = int(np.clip(round(t0 - ntr / 2), 0, g.shape[1] - ntr))
            g[i0:i1 + 1, j:j + ntr] = True
            return co + (j + ntr / 2) * p, True
        j = int(js[np.argmin(np.abs(js + lo + ntr / 2 - t0))]) + lo
        g[i0:i1 + 1, j:j + ntr] = True
        return co + (j + ntr / 2) * p, False

    def mark(self, horiz, c, ntr, a, b):
        g = self.g[horiz]
        so = self.o[0] if horiz else self.o[1]
        co = self.o[1] if horiz else self.o[0]
        i0 = max(0, int((min(a, b) - so) // self.sb))
        i1 = min(g.shape[0] - 1, int((max(a, b) - so) // self.sb))
        j = max(0, int(round((c - co) / self.p[horiz] - ntr / 2)))
        g[i0:i1 + 1, j:j + ntr] = True


def dedupe(pts):
    out = []
    for p in pts:
        p = (round(p[0], 3), round(p[1], 3))
        if not out or p != out[-1]:
            out.append(p)
    # drop collinear middle points
    res = []
    for p in out:
        while len(res) >= 2 and ((res[-2][0] == res[-1][0] == p[0]) or (res[-2][1] == res[-1][1] == p[1])):
            res.pop()
        res.append(p)
    return res


def stage_plan(L, blocks_on_path, reach, rep, mode):
    """blocks_on_path: [(rid, t_in, t_out)] sorted.  -> (regs [(t, where)], reps [(t, where)])."""
    regs = []
    for rid, ti, to in blocks_on_path:
        ln = to - ti
        if mode == "single" and ln <= reach:
            regs.append(((ti + to) / 2, rid))
            continue
        a, b = ti + min(PIN_INSET_UM, ln / 4), to - min(PIN_INSET_UM, ln / 4)
        n_int = max(0, int(math.ceil((b - a) / reach)) - 1)
        pts = [a] + [a + (b - a) * (j + 1) / (n_int + 1) for j in range(n_int)] + [b]
        regs.extend((t, rid) for t in pts)
    regs.sort()
    full = [(0.0, "src")] + regs + [(L, "dst")]
    out_regs = list(regs)
    for i in range(len(full) - 1):
        gap = full[i + 1][0] - full[i][0]
        if gap > reach:
            n = int(math.ceil(gap / reach)) - 1
            for j in range(n):
                out_regs.append((full[i][0] + gap * (j + 1) / (n + 1), None))
    out_regs.sort()
    full = [(0.0, "src")] + out_regs + [(L, "dst")]
    reps = []
    for i in range(len(full) - 1):
        gap = full[i + 1][0] - full[i][0]
        n = max(0, int(math.ceil(gap / rep)) - 1)
        for j in range(n):
            reps.append(full[i][0] + gap * (j + 1) / (n + 1))
    return out_regs, reps


def where(t, blocks_on_path):
    for rid, ti, to in blocks_on_path:
        if ti <= t <= to:
            return rid
    return None


def run(die, census_path, dump_dir, out_dir, policy="straight", ft_reg="inout", ft_clock="block",
        kinds=("data", "ctl"), forbid_re=FORBID_RE, slot_um=0.0, occupancy=0.6, max_shift_um=1500.0, png=True,
        min_track_bits=8, band_jogs=False,
        **over):
    t0 = time.time()
    cen = load_census(census_path)
    cfg = dies.get(die, **{k: v for k, v in over.items() if v is not None})
    if over.get("reach_um") is None:
        cfg["reach_um"] = cen["summary"]["reach_um"]
    reach, rep = cfg["reach_um"], cfg["rep_um"]
    dump = Dump(dump_dir)
    ftl = tuple(cen["summary"].get("ft_layers") or cfg["ft_layers"])
    lay_h, pitch_h = ft_layer(dump, ftl, True)
    lay_v, pitch_v = ft_layer(dump, ftl, False)
    fre = re.compile(forbid_re, re.I) if forbid_re else None

    blocks = {b["inst"]: b for b in cen["blocks"]}
    forbidden = set()
    for n, b in blocks.items():
        ms = [b["master"]] + (b.get("member_masters") or [])
        if fre and any(fre.search(m) for m in ms):
            forbidden.add(n)
    rects = [(n, b["x"], b["y"], b["w"], b["h"]) for n, b in blocks.items()]
    idx = census_mod.RectIndex(rects)
    member_owner = {}
    if cen["config"].get("merge_gap_um"):
        nonrelay = [i for i in dump.insts.values() if not re.search(cfg["relay_re"], i.master)]
        for reg, mem in census_mod.merge_regions(nonrelay, cen["config"]["merge_gap_um"],
                                                 cen["config"].get("merge_min_um2", 0.0)):
            if reg.name in blocks:
                for m in mem:
                    member_owner[m] = reg.name

    def tracks_of(b, face):
        length = b["h"] if face in ("W", "E") else b["w"]
        return length / (pitch_h if face in ("W", "E") else pitch_v)

    lanes = [g for g in cen["groups"] if g["kind"] in kinds]
    lanes.sort(key=lambda g: -g["bits"] * max(1.0, g["straight_um"]))
    face_load = defaultdict(float)
    die_box = dump.die["die"]
    tr = Tracks(die_box, pitch_h, pitch_v)
    out_lanes = []
    n_overflow = 0
    # broadcast source buses (the groups out of it carry more bits than the bus has): only those share a trunk band
    src_sum = defaultdict(int)
    for g in lanes:
        src_sum[(g["src"], g["src_bus"])] += g["bits"]
    broadcast = set()
    for (si, sb), tot in src_sum.items():
        inst = dump.insts.get(si)
        m = dump.masters.get(inst.master) if inst else None
        if m and sb in m.buses and tot > m.buses[sb].nbits:
            broadcast.add((si, sb))
    trunks = defaultdict(list)      # (src, src_bus, horiz) -> [(c, ntr)]: first leg of a broadcast / tap tree

    def place(horiz, c0, ntr, a, b, skey, shift=None):
        """the first leg out of a source bus reuses an existing band of the same source (a broadcast or tapped bus
        shares its trunk: those bits are on the wire once) when one is within max_shift and wide enough."""
        if skey is not None:
            for c, n in trunks[skey + (horiz,)]:
                if n >= ntr and abs(c - c0) <= max_shift_um:
                    tr.mark(horiz, c, ntr, a, b)
                    return c, False
        c, of = tr.place(horiz, c0, ntr, a, b, max_shift_um if shift is None else shift, slot_um)
        if skey is not None:
            trunks[skey + (horiz,)].append((c, ntr))
        return c, of

    for li, g in enumerate(lanes):
        sp, dp = tuple(g["src_pt"]), tuple(g["dst_pt"])
        skey = (g["src"], g["src_bus"]) if (g["src"], g["src_bus"]) in broadcast else None
        skip = {g["src"], g["dst"], member_owner.get(g["src"]), member_owner.get(g["dst"])}
        orders = ("HV",) if policy == "row" else ("HV", "VH")
        if policy == "row":
            orders = ("HV", "VH")   # VH only as the fallback when HV hits hard IP
        best = None
        for oi, order in enumerate(orders):
            pts = geom.l_route(sp, dp, order)
            cr = idx.crossings(pts, skip)
            if any(c[0] in forbidden for c in cr):
                continue
            cost = geom.manhattan(sp, dp)
            for rid, ln, fi, fo, ti, to in cr:
                for f in (fi, fo):
                    if f:
                        cost += 4.0 * (face_load[(rid, f)] + g["bits"]) / max(1.0, occupancy * tracks_of(blocks[rid], f))
            if policy == "row" and oi > 0:
                cost += 1e6
            if best is None or cost < best[0]:
                best = (cost, order, pts, cr)
        rec = dict(id=f"L{li}", src=g["src"], src_bus=g["src_bus"], dst=g["dst"], dst_bus=g["dst_bus"], kind=g["kind"],
                   bits=g["bits"], stages_old=g["stages"], straight_um=g["straight_um"], cur_um=g["cur_um"],
                   relays=g.get("relays", []))
        if best is None:
            n = geom.ideal_stages(g["cur_um"], reach)
            rec.update(keep_channel=True, route=None, pts=None, segments=[], stages_new=n,
                       reps=max(0, int(math.ceil(g["cur_um"] / rep)) - 1 - n))
            out_lanes.append(rec)
            continue
        _, order, pts, cr = best
        for rid, ln, fi, fo, ti, to in cr:
            for f in (fi, fo):
                if f:
                    face_load[(rid, f)] += g["bits"]
        # track bands
        ovf = False
        ntr = n_tracks(g["bits"], occupancy, ft_clock)
        of3 = of4 = False
        if g["bits"] < min_track_bits:      # thin control lanes keep their natural coordinate
            of1 = of2 = False
            y1, x2, x1, y2 = sp[1], dp[0], sp[0], dp[1]
            pts = dedupe(geom.l_route(sp, dp, order))
        elif order == "HV":
            y1, of1 = place(True, sp[1], ntr, sp[0], dp[0], skey)
            x2, of2 = place(False, dp[0], ntr, y1, dp[1], None)
            # end jogs (pin -> band) get their own bands so lanes leaving one pin do not stack on one track
            xj, of3 = (place(False, sp[0], ntr, sp[1], y1, None, JOG_SHIFT_UM) if band_jogs and abs(y1 - sp[1]) > JOG_MIN_UM
                       else (sp[0], False))
            ye, of4 = (place(True, dp[1], ntr, x2, dp[0], None, JOG_SHIFT_UM) if band_jogs and abs(x2 - dp[0]) > JOG_MIN_UM
                       else (dp[1], False))
            pts = dedupe([sp, (xj, sp[1]), (xj, y1), (x2, y1), (x2, ye), (dp[0], ye), dp])
        else:
            x1, of1 = place(False, sp[0], ntr, sp[1], dp[1], skey)
            y2, of2 = place(True, dp[1], ntr, x1, dp[0], None)
            yj, of3 = (place(True, sp[1], ntr, sp[0], x1, None, JOG_SHIFT_UM) if band_jogs and abs(x1 - sp[0]) > JOG_MIN_UM
                       else (sp[1], False))
            xe, of4 = (place(False, dp[0], ntr, y2, dp[1], None, JOG_SHIFT_UM) if band_jogs and abs(y2 - dp[1]) > JOG_MIN_UM
                       else (dp[0], False))
            pts = dedupe([sp, (sp[0], yj), (x1, yj), (x1, y2), (xe, y2), (xe, dp[1]), dp])
        ovf = of1 or of2 or of3 or of4
        n_overflow += int(ovf)
        L = geom.polyline_len(pts)
        cr = idx.crossings(pts, skip)
        bop = [(rid, ti, to) for rid, ln, fi, fo, ti, to in cr]
        regs, reps = stage_plan(L, bop, reach, rep, ft_reg)
        segs = []
        for rid, ln, fi, fo, ti, to in cr:
            pin = geom.point_at(pts, ti)
            pout = geom.point_at(pts, to)
            segs.append(dict(kind="block", block=rid, t_in=round(ti, 1), t_out=round(to, 1), len_um=round(ln, 1),
                             face_in=fi, face_out=fo, p_in=[round(pin[0], 3), round(pin[1], 3)],
                             p_out=[round(pout[0], 3), round(pout[1], 3)],
                             stages=sum(1 for t, w in regs if w == rid),
                             reps=sum(1 for t in reps if ti <= t <= to),
                             regs_t=[round(t, 1) for t, w in regs if w == rid]))
        ch_regs = [t for t, w in regs if w is None]
        rec.update(keep_channel=False, route=order, pts=[list(p) for p in pts], len_um=round(L, 1), segments=segs,
                   channel_stages=len(ch_regs), channel_regs_t=[round(t, 1) for t in ch_regs],
                   stages_new=len(regs), reps=len(reps), track_overflow=ovf)
        out_lanes.append(rec)

    # ---- per-block ft specs ---------------------------------------------------------------------------------------
    specs = defaultdict(lambda: dict(ports=[], paths=[]))
    for lane in out_lanes:
        for s in lane["segments"]:
            rid = s["block"]
            b = blocks[rid]
            inst = dump.insts.get(rid)
            W, H, orient, x0, y0 = b["w"], b["h"], "R0", b["x"], b["y"]
            if inst is not None and inst.master in dump.masters:
                m = dump.masters[inst.master]
                W, H, orient = m.w, m.h, inst.orient
            sp_ = specs[rid]
            # a broadcast trunk shared by several lanes crosses the block once
            tkey = (lane["src"], lane["src_bus"], tuple(s["p_in"]), tuple(s["p_out"]))
            if tkey in sp_.setdefault("_trunks", {}):
                sp_["paths"][sp_["_trunks"][tkey]].setdefault("shared_lanes", []).append(lane["id"])
                continue
            k = len(sp_["paths"])
            sp_["_trunks"][tkey] = k
            horiz_in = s["face_in"] in ("W", "E") if s["face_in"] else None

            def port(name, d, p, face_die):
                mx, my = inv_xform(p[0], p[1], W, H, orient, x0, y0)
                face = geom.nearest_face(mx, my, 0, 0, W, H)
                horiz = face in ("W", "E")
                pitch = pitch_h if horiz else pitch_v
                width = n_tracks(lane["bits"], occupancy, ft_clock) * pitch     # = the lane's track band
                off = my if horiz else mx
                return dict(name=name, path=k, dir=d, face=face, lo=round(off - width / 2, 3),
                            hi=round(off + width / 2, 3), layer=lay_h if horiz else lay_v, bits=lane["bits"],
                            die_xy=p)
            pi = port(f"ft{k}_i", "input", s["p_in"], s["face_in"])
            po = port(f"ft{k}_o", "output", s["p_out"], s["face_out"])
            sp_["ports"] += [pi, po]
            regs_xy = []
            for t in s["regs_t"]:
                p = geom.point_at([tuple(x) for x in lane["pts"]], t)
                regs_xy.append([round(v, 1) for v in inv_xform(p[0], p[1], W, H, orient, x0, y0)])
            sp_["paths"].append(dict(path=k, lane=lane["id"], src=f"{lane['src']}/{lane['src_bus']}",
                                     dst=f"{lane['dst']}/{lane['dst_bus']}", **{"in": pi["name"], "out": po["name"]},
                                     bits=lane["bits"], stages=s["stages"], len_um=s["len_um"], rep_sites=s["reps"],
                                     regs_um=regs_xy))
            del horiz_in
    os.makedirs(os.path.join(out_dir, "ftspec"), exist_ok=True)
    variants = defaultdict(lambda: defaultdict(list))
    for rid, sp_ in specs.items():
        sp_.pop("_trunks", None)
        b = blocks[rid]
        inst = dump.insts.get(rid)
        sig = sorted((p["dir"], p["face"], round(p["lo"], 1), round(p["hi"], 1), p["layer"], p["bits"])
                     for p in sp_["ports"]) + sorted((q["bits"], q["stages"]) for q in sp_["paths"])
        h = hashlib.sha1(json.dumps(sig).encode()).hexdigest()[:8]
        master = b["master"]
        variant = f"{master}__ft{h}"
        variants[master][variant].append(rid)
        W, H = (dump.masters[inst.master].w, dump.masters[inst.master].h) if inst is not None and \
            inst.master in dump.masters else (b["w"], b["h"])
        spec = dict(schema=SPEC_SCHEMA, die=die, block=rid, master=master, variant=variant, outline=[W, H],
                    orient=inst.orient if inst is not None else "R0", die_bbox=[b["x"], b["y"], b["w"], b["h"]],
                    members=b.get("members"),
                    layer_contract=dict(signal_max="M7", ft_layers=list(ftl), pg_max="M7"), clock=ft_clock,
                    reach_um=reach, rep_um=rep, ft_reg=ft_reg, ports=sp_["ports"], paths=sp_["paths"],
                    ft_bits=sum(q["bits"] for q in sp_["paths"]),
                    ft_bit_stages=sum(q["bits"] * q["stages"] for q in sp_["paths"]))
        with open(os.path.join(out_dir, "ftspec", f"{rid.replace('/', '_').replace(':', '_')}.json"), "w") as f:
            json.dump(spec, f, indent=1)

    # port bands that overlap on one face (track overflow lanes, and lanes leaving one pin face whose jogs cross a
    # block at the same spot): reported, the abstract probe drops them
    import checks as checks_mod
    overlap_bits = 0
    for rid, sp_ in specs.items():
        _, dr = checks_mod.dedupe_pins(checks_mod.ft_pins(dict(outline=[1e9, 1e9], ports=sp_["ports"],
                                                               paths=sp_["paths"])))
        overlap_bits += dr

    # ---- summary --------------------------------------------------------------------------------------------------
    bits = sum(l["bits"] for l in out_lanes) or 1
    st_old = sum(l["bits"] * l["stages_old"] for l in out_lanes)
    st_new = sum(l["bits"] * l["stages_new"] for l in out_lanes)
    summary = dict(die=die, policy=policy, ft_reg=ft_reg, ft_clock=ft_clock, reach_um=reach, rep_um=rep,
                   occupancy=occupancy, slot_um=slot_um, lanes=len(out_lanes), bits=bits,
                   keep_channel=sum(1 for l in out_lanes if l["keep_channel"]),
                   forbidden_blocks=sorted(forbidden)[:40], n_forbidden=len(forbidden),
                   stages_old_sum=sum(l["stages_old"] for l in out_lanes),
                   stages_new_sum=sum(l["stages_new"] for l in out_lanes),
                   stages_old_bitw=round(st_old / bits, 2), stages_new_bitw=round(st_new / bits, 2),
                   bit_stage_cut=round(1 - st_new / max(1, st_old), 3),
                   channel_relays_new=sum(l.get("channel_stages", 0) for l in out_lanes if not l["keep_channel"]),
                   lanes_with_ft=sum(1 for l in out_lanes if l["segments"]), host_blocks=len(specs),
                   variants=sum(len(v) for v in variants.values()), masters_hosting=len(variants),
                   track_overflow_lanes=n_overflow, port_overlap_bits=overlap_bits, max_stages_new=max((l["stages_new"] for l in out_lanes), default=0),
                   seconds=round(time.time() - t0, 1))
    js = dict(schema=SCHEMA, summary=summary, census=str(census_path),
              variants={m: dict(v) for m, v in variants.items()}, lanes=out_lanes)
    with open(os.path.join(out_dir, f"{die}_plan.json"), "w") as f:
        json.dump(js, f, separators=(",", ":"))
    with open(os.path.join(out_dir, f"{die}_schedule.tsv"), "w") as f:
        f.write("lane\tsrc\tsrc_bus\tdst\tdst_bus\tbits\tstages_old\tstages_new\tkeep_channel\n")
        for l in out_lanes:
            f.write(f"{l['id']}\t{l['src']}\t{l['src_bus']}\t{l['dst']}\t{l['dst_bus']}\t{l['bits']}\t"
                    f"{l['stages_old']}\t{l['stages_new']}\t{int(l['keep_channel'])}\n")
    if png:
        draw(js, blocks, forbidden, specs, dump, os.path.join(out_dir, f"{die}_plan.png"))
    return js


def draw(js, blocks, forbidden, specs, dump, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    d = dump.die["die"]
    W, H = d[2] - d[0], d[3] - d[1]
    fig, ax = plt.subplots(figsize=(12, 12 * H / W + 0.8))
    mx = max((sp_["ft_bits"] if "ft_bits" in sp_ else sum(q["bits"] for q in sp_["paths"]))
             for sp_ in specs.values()) if specs else 1
    cmap = plt.get_cmap("Blues")
    for n, b in blocks.items():
        if n in forbidden:
            fc = "#e8a0a0"
        elif n in specs:
            fc = cmap(0.2 + 0.7 * sum(q["bits"] for q in specs[n]["paths"]) / mx)
        else:
            fc = "#eeeeee"
        ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc=fc, ec="#666", lw=0.3))
    top = sorted((l for l in js["lanes"] if l["pts"]), key=lambda l: -l["bits"] * l["len_um"])[:400]
    for l in top:
        xs = [p[0] for p in l["pts"]]
        ys = [p[1] for p in l["pts"]]
        ax.plot(xs, ys, lw=0.3 + l["bits"] / 500, c="#c0392b", alpha=0.5)
        for s in l["segments"]:
            for t in s["regs_t"]:
                p = geom.point_at([tuple(x) for x in l["pts"]], t)
                ax.plot(p[0], p[1], "k.", ms=1.5)
    s = js["summary"]
    ax.set_xlim(d[0], d[2])
    ax.set_ylim(d[1], d[3])
    ax.set_aspect("equal")
    ax.set_title(f"{s['die']} ft plan ({s['policy']}, {s['ft_reg']}): bit-weighted stages {s['stages_old_bitw']} -> "
                 f"{s['stages_new_bitw']}; {s['host_blocks']} host blocks, {s['variants']} variants of "
                 f"{s['masters_hosting']} masters; red = hard IP (no ft); dots = in-block registers", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--die", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--policy", choices=("straight", "row"), default="straight")
    ap.add_argument("--ft-reg", choices=("inout", "single"), default="inout")
    ap.add_argument("--ft-clock", choices=("block", "forwarded"), default=None)
    ap.add_argument("--kinds", default="data,ctl")
    ap.add_argument("--forbid-re", default=FORBID_RE)
    ap.add_argument("--slot-um", type=float, default=0.0)
    ap.add_argument("--occupancy", type=float, default=0.6)
    ap.add_argument("--max-shift-um", type=float, default=1500.0)
    ap.add_argument("--reach-um", type=float)
    ap.add_argument("--rep-um", type=float)
    ap.add_argument("--band-jogs", action="store_true", help="give pin->band jogs their own bands (more overflow)")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args(argv)
    ft_clock = a.ft_clock or ("forwarded" if a.die == "s81" else "block")
    js = run(a.die, a.census, a.dump, a.out, policy=a.policy, ft_reg=a.ft_reg, ft_clock=ft_clock,
             kinds=tuple(a.kinds.split(",")), forbid_re=a.forbid_re, slot_um=a.slot_um, occupancy=a.occupancy,
             max_shift_um=a.max_shift_um, png=not a.no_png, band_jogs=a.band_jogs, reach_um=a.reach_um, rep_um=a.rep_um)
    print(json.dumps(js["summary"], indent=1))


if __name__ == "__main__":
    main()
