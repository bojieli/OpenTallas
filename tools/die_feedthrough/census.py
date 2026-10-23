#!/usr/bin/env python3
"""Die feedthrough census (FT-TOOL, FT-PLAN owner 10-23).

    census.py --die {s81,kv,qc,hbm} --dump DUMPDIR --out OUTDIR [--reach-um R] [--rep-um 450]
              [--big-min-um2 1e5] [--ft-layers M8,M9] [--no-png]

DUMPDIR is the output of dump.sh / odb_dump.py on the die ODB (real connectivity through buffers).

Per LANE GROUP (relay chains from one source block bus to one sink block bus; lanes.py):
  bits, current stages (relays on the longest chain), landings, current length (Manhattan through the relay centres),
  straight length (Manhattan pin to pin), detour, ideal stages at the die reach, and the straight Manhattan L route
  (HV or VH, whichever crosses fewer big blocks) with every big block it crosses: face in / out, length inside,
  ideal stage count that falls inside the block.
Per BIG BLOCK (non-relay, >= big_min_um2): ft bits per face, the face's M8/M9 track capacity (wires crossing a W/E face
  run on the horizontal ft layers, N/S on the vertical ones), bits/tracks total and peak over 50-um bins (limit 0.6),
  OBS cover of the ft layers (1.0 = full blanket: over-the-top routing impossible until the layer contract changes),
  lanes crossing, ideal in-block stages.
Outputs: OUTDIR/<die>_census.json (summary + blocks + lane groups), OUTDIR/<die>_lanes.tsv (one row per lane group),
OUTDIR/<die>_census.png.  Schema opentallas.die_feedthrough.census.v1.  Exit 0 (a census, not a gate).
"""
import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dies  # noqa: E402
import geom  # noqa: E402
import lanes as lanes_mod  # noqa: E402
from dump_io import Dump  # noqa: E402

SCHEMA = "opentallas.die_feedthrough.census.v1"
BIN_UM = 50.0
RST_RE = re.compile(r"(^|_)(rs|rst|rst_n|rstn|reset)(_|$)", re.I)


class RectIndex:
    """bucketed rectangles for axis-parallel segment queries."""

    def __init__(self, rects, bucket=250.0):
        self.b = bucket
        self.rows = defaultdict(list)   # y bucket -> rects (for horizontal segments)
        self.cols = defaultdict(list)   # x bucket -> rects (for vertical segments)
        for r in rects:
            rid, x, y, w, h = r
            for k in range(int(y // bucket), int((y + h) // bucket) + 1):
                self.rows[k].append(r)
            for k in range(int(x // bucket), int((x + w) // bucket) + 1):
                self.cols[k].append(r)
        self.all = rects

    def cands(self, a, b):
        if a[1] == b[1]:
            return self.rows.get(int(a[1] // self.b), ())
        if a[0] == b[0]:
            return self.cols.get(int(a[0] // self.b), ())
        return self.all

    def crossings(self, pts, skip=()):
        res = []
        t0 = 0.0
        for i in range(len(pts) - 1):
            for rid, ln, fi, fo, ti, to in sorted(geom.seg_crossings(pts[i], pts[i + 1], self.cands(pts[i], pts[i + 1]),
                                                                      skip), key=lambda c: c[4]):
                if res and res[-1][0] == rid and abs(res[-1][5] - (t0 + ti)) < 1e-6:
                    r = res[-1]
                    res[-1] = (rid, r[1] + ln, r[2], fo, r[4], t0 + to)
                else:
                    res.append((rid, ln, fi, fo, t0 + ti, t0 + to))
            t0 += geom.manhattan(pts[i], pts[i + 1])
        return res

    def containing(self, x, y):
        for rid, rx, ry, rw, rh in self.rows.get(int(y // self.b), ()):
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return rid
        return None


def merge_regions(insts, gap, min_um2=0.0):
    """union blocks whose outlines are within gap um of each other (a tiled array of small blocks is one obstacle
    for a die wire).  -> [(Inst region (name 'region:<first>+N', master 'REGION'), [member names])]."""
    from dump_io import Inst
    cand = [i for i in insts if i.w * i.h >= min_um2]
    parent = list(range(len(cand)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    B = 200.0
    grid = defaultdict(list)
    for k, i in enumerate(cand):
        for gx in range(int((i.x - gap) // B), int((i.x + i.w + gap) // B) + 1):
            for gy in range(int((i.y - gap) // B), int((i.y + i.h + gap) // B) + 1):
                grid[(gx, gy)].append(k)
    for cell in grid.values():
        for a_ in range(len(cell)):
            ia = cand[cell[a_]]
            for b_ in range(a_ + 1, len(cell)):
                ib = cand[cell[b_]]
                if (ia.x - gap <= ib.x + ib.w and ib.x - gap <= ia.x + ia.w and ia.y - gap <= ib.y + ib.h
                        and ib.y - gap <= ia.y + ia.h):
                    ra, rb = find(cell[a_]), find(cell[b_])
                    if ra != rb:
                        parent[ra] = rb
    comp = defaultdict(list)
    for k in range(len(cand)):
        comp[find(k)].append(cand[k])
    out = []
    for mem in comp.values():
        x0 = min(i.x for i in mem); y0 = min(i.y for i in mem)
        x1 = max(i.x + i.w for i in mem); y1 = max(i.y + i.h for i in mem)
        if len(mem) == 1:
            out.append((mem[0], [mem[0].name]))
            continue
        name = f"region:{sorted(i.name for i in mem)[0]}+{len(mem) - 1}"
        out.append((Inst(name, "REGION", x0, y0, x1 - x0, y1 - y0), [i.name for i in mem]))
    return out


def bus_point(dump, inst_name, bus_name):
    """die coordinate of the centre of a bus's pins on a placed block; None for PORT / CELL / unknown."""
    inst = dump.insts.get(inst_name)
    if inst is None:
        return None
    m = dump.masters.get(inst.master)
    if m is None:
        return (inst.cx, inst.cy)
    b = m.buses.get(bus_name)
    if b is None:
        return (inst.cx, inst.cy)
    px, py = geom.face_point(b.face, b.lo, b.hi, m.w, m.h)
    try:
        return geom.xform(px, py, m.w, m.h, inst.orient, inst.x, inst.y)
    except ValueError:
        return (inst.cx, inst.cy)


def face_tracks(dump, layers, face, length):
    """M8/M9 tracks that cross a face of the given length: W/E faces are crossed by horizontal wires."""
    want = "HORIZONTAL" if face in ("W", "E") else "VERTICAL"
    t = 0.0
    for ln in layers:
        L = dump.layer(ln)
        if L and L["dir"] == want and L["pitch"] > 0:
            t += length / L["pitch"]
    return t


def run(die, dump_dir, out_dir, png=True, **over):
    t0 = time.time()
    cfg = dies.get(die, **over)
    dump = Dump(dump_dir)
    reach = cfg["reach_um"]
    groups, relay_map, lstats = lanes_mod.extract(dump, cfg["relay_re"], cfg.get("land_re"))

    relay_names = {n for n, i in dump.insts.items() if i.master in relay_map}
    rre = re.compile(cfg["relay_re"])
    relays_by_kind = defaultdict(int)
    for n in relay_names:
        mn = dump.insts[n].master
        nb = max((dump.masters[mn].buses[i].nbits for i in relay_map[mn] if i in dump.masters[mn].buses), default=0)
        relays_by_kind["reset" if re.search(r"rst", mn) else ("data" if nb > 8 else "ctl")] += 1
    nonrelay = [i for n, i in dump.insts.items() if not (rre.search(i.master) or i.master in relay_map)]
    big = {}
    members = {}
    if cfg.get("merge_gap_um"):
        for reg, mem in merge_regions(nonrelay, cfg["merge_gap_um"], cfg.get("merge_min_um2", 0.0)):
            if reg.w * reg.h >= cfg["big_min_um2"]:
                big[reg.name] = reg
                members[reg.name] = mem
    else:
        for i in nonrelay:
            if i.w * i.h >= cfg["big_min_um2"]:
                big[i.name] = i
    # lanes ending on a member of a merged region start / end at that region
    owner = {m: r for r, mem in members.items() for m in mem}
    rects = [(n, i.x, i.y, i.w, i.h) for n, i in big.items()]
    idx = RectIndex(rects)
    ft_layers = tuple(cfg["ft_layers"])

    # relays sitting inside a big block footprint
    rel_inside = 0
    for n in relay_names:
        i = dump.insts[n]
        if idx.containing(i.cx, i.cy) is not None:
            rel_inside += 1

    bstat = {n: dict(faces=defaultdict(int), bins=defaultdict(lambda: defaultdict(int)), lanes=0, bits=0,
                     stages_in=0, bit_stages_in=0, crossed_um=0.0) for n in big}
    out_groups = []
    tot = defaultdict(float)
    for g in groups:
        sp = bus_point(dump, g["src"], g["src_bus"])
        dp = bus_point(dump, g["dst"], g["dst_bus"])
        path = list(g["path"])
        rpts = [(dump.insts[r].cx, dump.insts[r].cy) for r in path]
        if sp is None:
            sp = rpts[0] if rpts else None
        if dp is None:
            dp = rpts[-1] if rpts else None
        if sp is None or dp is None:
            continue
        cur = geom.polyline_len([sp] + rpts + [dp])
        straight = geom.manhattan(sp, dp)
        skip = {g["src"], g["dst"], owner.get(g["src"]), owner.get(g["dst"])}
        best = None
        for order in ("HV", "VH"):
            pts = geom.l_route(sp, dp, order)
            cr = idx.crossings(pts, skip)
            key = (len(cr), sum(c[1] for c in cr))
            if best is None or key < best[0]:
                best = (key, order, pts, cr)
        _, order, pts, cr = best
        n_ideal = geom.ideal_stages(straight, reach)
        spos = geom.stage_positions(straight, n_ideal)
        crs = []
        for rid, ln, fi, fo, ti, to in cr:
            k_in = sum(1 for s in spos if ti <= s <= to)
            crs.append(dict(block=rid, um=round(ln, 1), face_in=fi, face_out=fo, stages_in=k_in,
                            t_in=round(ti, 1), t_out=round(to, 1)))
            b = bstat[rid]
            b["lanes"] += 1
            b["bits"] += g["bits"]
            b["stages_in"] += k_in
            b["bit_stages_in"] += k_in * g["bits"]
            b["crossed_um"] += ln
            bi = big[rid]
            for face, t in ((fi, ti), (fo, to)):
                if face is None:
                    continue
                p = geom.point_at(pts, t)
                off = (p[0] - bi.x) if face in "NS" else (p[1] - bi.y)
                b["faces"][face] += g["bits"]
                b["bins"][face][int(max(0.0, off) // BIN_UM)] += g["bits"]
        kind = "reset" if (g["rst"] or RST_RE.search(g["src_bus"]) or RST_RE.search(g["dst_bus"])) else ("ctl" if g["bits"] <= 8 else "data")
        rec = dict(src=g["src"], src_bus=g["src_bus"], dst=g["dst"], dst_bus=g["dst_bus"], kind=kind,
                   bits=g["bits"], chains=g["chains"], stages=g["stages_max"], stages_min=g["stages_min"],
                   lands=g["lands"], nbuf_max=g["nbuf_max"], cur_um=round(cur, 1), straight_um=round(straight, 1),
                   detour=round(cur / straight, 3) if straight > 0 else None, ideal_stages=n_ideal, route=order,
                   src_pt=[round(sp[0], 1), round(sp[1], 1)], dst_pt=[round(dp[0], 1), round(dp[1], 1)],
                   crosses=crs, relays=path)
        out_groups.append(rec)
        tot["bits"] += g["bits"]
        tot["bit_stages_cur"] += g["bits"] * g["stages_max"]
        tot["bit_stages_ideal"] += g["bits"] * n_ideal
        tot["bitmm_cur"] += g["bits"] * cur / 1000
        tot["bitmm_straight"] += g["bits"] * straight / 1000
        if crs:
            tot["groups_crossing"] += 1
            tot["bits_crossing"] += g["bits"]

    blocks_out = []
    over_limit = 0
    for n, b in bstat.items():
        i = big[n]
        m = dump.masters.get(i.master)
        if n in members:     # merged region: worst member cover
            ms = [dump.masters.get(dump.insts[x].master) for x in members[n]]
            cover = {L: max((mm.obs_cover.get(L, 0.0) for mm in ms if mm), default=0.0) for L in ft_layers}
            m = max((mm for mm in ms if mm), key=lambda mm: mm.w * mm.h, default=None)
        else:
            cover = {L: (m.obs_cover.get(L, 0.0) if m else None) for L in ft_layers}
        faces = {}
        worst = 0.0
        for face, bits in b["faces"].items():
            length = i.h if face in ("W", "E") else i.w
            tr = face_tracks(dump, ft_layers, face, length)
            bin_tr = face_tracks(dump, ft_layers, face, BIN_UM)
            peak = max(b["bins"][face].values()) if b["bins"][face] else 0
            r_tot = bits / tr if tr else math.inf
            r_peak = peak / bin_tr if bin_tr else math.inf
            faces[face] = dict(bits=bits, tracks=int(tr), ratio=round(r_tot, 3), peak_bin_bits=peak,
                               peak_ratio=round(r_peak, 3))
            worst = max(worst, r_tot)
        if worst > cfg["ft_ratio_max"]:
            over_limit += 1
        blocks_out.append(dict(inst=n, master=i.master, x=i.x, y=i.y, w=i.w, h=i.h, area_mm2=round(i.w * i.h / 1e6, 3),
                               obs_top=(m.obs_top() if m else None), ft_obs_cover=cover,
                               ft_blocked=any((c or 0) > 0.5 for c in cover.values()),
                               lanes=b["lanes"], bits=b["bits"], crossed_bit_mm=None, stages_in=b["stages_in"],
                               bit_stages_in=b["bit_stages_in"], faces=faces, worst_ratio=round(worst, 3),
                               members=len(members.get(n, ())) or None,
                               member_masters=(sorted({dump.insts[x].master for x in members[n]})[:12]
                                               if n in members else None)))
    blocks_out.sort(key=lambda r: -r["bits"])

    # unique bits: a broadcast / tapped source bus is on the wire once -> per source bus min(sum of groups, bus width)
    per_src = defaultdict(int)
    for g in out_groups:
        per_src[(g["src"], g["src_bus"])] += g["bits"]
    bits_unique = 0
    for (si, sb), b in per_src.items():
        inst = dump.insts.get(si)
        m = dump.masters.get(inst.master) if inst else None
        w = m.buses[sb].nbits if m and sb in m.buses else b
        bits_unique += min(b, w)
    die_box = dump.die["die"]
    die_area = (die_box[2] - die_box[0]) * (die_box[3] - die_box[1])
    big_area = sum(i.w * i.h for i in big.values())
    data = [g for g in out_groups if g["kind"] == "data"]
    summary = dict(
        die=die, label=cfg["label"], odb=dump.die.get("odb"), reach_um=reach, rep_um=cfg["rep_um"],
        ft_layers=list(ft_layers), die_um=[die_box[2] - die_box[0], die_box[3] - die_box[1]],
        big_blocks=len(big), big_area_frac=round(big_area / die_area, 3),
        big_blocks_ft_blocked=sum(1 for b in blocks_out if b["ft_blocked"]),
        relays=len(relay_names), relays_by_kind=dict(relays_by_kind), relays_inside_big_pct=round(100.0 * rel_inside / max(1, len(relay_names)), 2),
        lane_groups=len(out_groups), data_groups=len(data), bits=int(tot["bits"]), bits_unique=int(bits_unique),
        stages_cur_bitw=round(tot["bit_stages_cur"] / max(1, tot["bits"]), 2),
        stages_ideal_bitw=round(tot["bit_stages_ideal"] / max(1, tot["bits"]), 2),
        stage_reduction=round(tot["bit_stages_cur"] / max(1, tot["bit_stages_ideal"]), 2),
        bitmm_cur=round(tot["bitmm_cur"]), bitmm_straight=round(tot["bitmm_straight"]),
        detour_bitw=round(tot["bitmm_cur"] / max(1e-9, tot["bitmm_straight"]), 3),
        groups_crossing_big=int(tot["groups_crossing"]), bits_crossing_big=int(tot["bits_crossing"]),
        blocks_with_ft=sum(1 for b in blocks_out if b["lanes"]), blocks_over_ratio=over_limit,
        max_stages=max((g["stages"] for g in out_groups), default=0),
        lanes_stats=lstats, hifan_drivers=len(dump.hifan), seconds=round(time.time() - t0, 1))
    os.makedirs(out_dir, exist_ok=True)
    js = dict(schema=SCHEMA, summary=summary, config={k: v for k, v in cfg.items() if k != "dump"},
              blocks=blocks_out, groups=out_groups, hifan=dump.hifan[:200])
    jp = os.path.join(out_dir, f"{die}_census.json")
    with open(jp, "w") as f:
        json.dump(js, f, indent=None, separators=(",", ":"))
    with open(os.path.join(out_dir, f"{die}_lanes.tsv"), "w") as f:
        f.write("src\tsrc_bus\tdst\tdst_bus\tkind\tbits\tchains\tstages\tideal\tcur_um\tstraight_um\tdetour\t"
                "route\tcrosses\n")
        for g in sorted(out_groups, key=lambda r: -r["bits"] * r["straight_um"]):
            f.write(f"{g['src']}\t{g['src_bus']}\t{g['dst']}\t{g['dst_bus']}\t{g['kind']}\t{g['bits']}\t{g['chains']}\t"
                    f"{g['stages']}\t{g['ideal_stages']}\t{g['cur_um']}\t{g['straight_um']}\t{g['detour']}\t"
                    f"{g['route']}\t{','.join(c['block'] for c in g['crosses'])}\n")
    if png:
        draw(js, dump, relay_names, os.path.join(out_dir, f"{die}_census.png"))
    return js


def draw(js, dump, relay_names, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    s = js["summary"]
    W, H = s["die_um"]
    fig, axs = plt.subplots(1, 2, figsize=(22, 22 * H / W / 2 + 1.5))
    # left: floorplan, relays, current chains of the biggest data lanes
    ax = axs[0]
    for b in js["blocks"]:
        ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc="#d9d9d9" if not b["ft_blocked"] else "#bfbfbf",
                               ec="#555", lw=0.3))
    xs = [dump.insts[n].cx for n in relay_names]
    ys = [dump.insts[n].cy for n in relay_names]
    ax.scatter(xs, ys, s=0.2, c="#c0392b", lw=0)
    top = sorted(js["groups"], key=lambda g: -g["bits"] * g["straight_um"])[:300]
    for g in top:
        pts = [g["src_pt"]] + [[dump.insts[r].cx, dump.insts[r].cy] for r in g["relays"]] + [g["dst_pt"]]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=0.4, c="#1f4e79", alpha=0.5)
    ax.set_title(f"{s['label']}: big blocks (grey; darker = OBS on M8/M9), {s['relays']} relays (red), "
                 f"top-300 lane chains (blue)", fontsize=9)
    # right: straight routes + face load
    ax = axs[1]
    cmap = plt.get_cmap("RdYlGn_r")
    for b in js["blocks"]:
        r = min(1.5, b["worst_ratio"]) / 1.5
        ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc=cmap(r) if b["lanes"] else "#eeeeee", ec="#555",
                               lw=0.3, alpha=0.8))
        if b["lanes"] and b["w"] * b["h"] > 0.02 * W * H:
            ax.text(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, f"{b['bits']}b\nr{b['worst_ratio']:.2f}",
                    ha="center", va="center", fontsize=6)
    for g in top:
        if g["kind"] != "data":
            continue
        sp, dp = g["src_pt"], g["dst_pt"]
        pts = geom.l_route(tuple(sp), tuple(dp), g["route"])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=0.3 + g["bits"] / 400, c="#1f4e79", alpha=0.4)
    ax.set_title(f"straight L routes (top-300 data lanes); block colour = worst face bits/M8-M9 tracks "
                 f"(green 0 -> red >=1.5; limit {js['config']['ft_ratio_max']})", fontsize=9)
    for a in axs:
        a.set_xlim(0, W)
        a.set_ylim(0, H)
        a.set_aspect("equal")
        a.tick_params(labelsize=6)
    fig.suptitle(f"{s['die']} census: {s['lane_groups']} lane groups, {s['bits']} bits, stages bit-weighted "
                 f"{s['stages_cur_bitw']} now vs {s['stages_ideal_bitw']} at reach {s['reach_um']:.0f} um, "
                 f"detour {s['detour_bitw']}, {s['bits_crossing_big']} bits cross big blocks", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--die", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reach-um", type=float)
    ap.add_argument("--rep-um", type=float)
    ap.add_argument("--big-min-um2", type=float)
    ap.add_argument("--ft-layers")
    ap.add_argument("--merge-gap-um", type=float, help="union blocks closer than this into one obstacle region")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args(argv)
    js = run(a.die, a.dump, a.out, png=not a.no_png, reach_um=a.reach_um, rep_um=a.rep_um,
             big_min_um2=a.big_min_um2, merge_gap_um=a.merge_gap_um, ft_layers=tuple(a.ft_layers.split(",")) if a.ft_layers else None)
    print(json.dumps(js["summary"], indent=1))


if __name__ == "__main__":
    main()
