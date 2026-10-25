#!/usr/bin/env python3
"""KV-405 10-24: plan v3.9 = v3.8x re-planned to owner decisions 12 / 17 and METHODOLOGY rulings 9.3 / 9.4
(ONE batched KV plan change): every signal on <= M7 (M8/M9 = die clock spine, die reset and PG only), every lane hop,
every ft station spacing and every internal-station hop <= 405 um EXACTLY (no 0.9 margin), die.reach_um 405,
layer_budget.die_use without ft_reserved.  Stations are re-derived by the tools here (no hand edits):

  1. die / budgets: die.reach_um 405; die_use drops ft_reserved; cut_avail M8/M9 0 (no signal capacity there);
     budgets.ft_station_max_um 405 and budgets.reach_margin 1.0 (the G0C reach check judges hops against 405 exactly).
  2. ft slot stations: stations = max(current, ceil(L / 405) over every lane crossing the slot (check.py lane_geometry,
     port-centroid zroute = the G0 hop / station measure), ceil(worst bit / 405) (tools/die_plan/ft_reach.py on the
     actual pin bits, margin 1.0)).  kv3_hub_Ei comes out IDENTICAL to Codex's reach405 sizing (codex/kv-hub-1024
     6dd64015fd die_plan_reach405.json, the slots the vK / vL / vM kits carry): asserted below when --codex is given.
     A slot whose count changes loses its regs_um (ft_channel_regs.py re-derives core-free sites on the new count);
     regs_um of every other slot are dropped too and re-derived (same tool, same result where the count is unchanged).
  3. internal_stations (R3-INTERNAL FIRM plan stations): every hop > 405 is split on an L leg (corner chosen so no new
     station falls in a hard core + 8.64 um); legs of one bus are padded to one depth (lane latency is per bus); every
     lane ending on / starting from that (partition, bus) gets fixed_cycles += the added depth.
  5. reset.release = "wavefront" (owner decision 13 / 17; tools/die_plan/reset_tree.py, claude/reset-1024 @0a08a66af):
     one root synchroniser per die + neighbour wavefront; per-partition release offsets published by run_v39.sh.
  6. qkd_ahub r2 (COORD ruling 5 on KV-CORES OWNER?, GEOM-REVIEW PASS-COND for the plan): hub_C core ahub outline
     734.4 x 540 -> 604.8 x 440.64, S-E corner fixed (pins: core_pins_v39.py).
  4. kv3_phy / kv3_phy_v1 reset.tap_um moved to the type E face (toward the pc_* neighbour in every orient: R0 / MX at
     the W edge, MY / R180 at the E edge), y unchanged: the RESET wavefront reports the centre tap 441 um from the
     nearest pc rst_o (lanes/RESET.md 22:25); at the E face the hop is ~30 um.

    usage: post_v39.py die_plan(v3.8x).json [--codex die_plan_reach405.json] [--report OUT.json] > die_plan.json"""
import copy
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import check as C       # noqa: E402
import ft_reach         # noqa: E402
import schema as S      # noqa: E402

REACH = S.SIGNAL_REACH_UM          # 405
CLEAR = 8.64
EPS = 1e-6
PHY_TYPES = ("kv3_phy", "kv3_phy_v1")
PHY_TAP_INSET = 21.6               # um inside the E face (2.5 x 8.64 lattice)


def need(L):
    return max(1, math.ceil(L / REACH - EPS))


def die_level(raw):
    d = raw["die"]
    old = dict(reach_um=d.get("reach_um"), die_use=list(d["layer_budget"].get("die_use", [])),
               cut_avail=d["layer_budget"].get("cut_avail"))
    d["reach_um"] = REACH
    lb = d["layer_budget"]
    lb["die_use"] = [u for u in lb.get("die_use", []) if u != "ft_reserved"]
    lb["cut_avail"] = {"M8": 0.0, "M9": 0.0}
    b = raw.setdefault("budgets", {})
    b["ft_station_max_um"] = REACH
    b["reach_margin"] = 1.0
    return old


def size_slots(raw, codex=None):
    P = S.Plan(raw)
    geo = defaultdict(float)
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            s = P.slot(part, slot) or {}
            seg = C.zroute(P.port_point(a), P.port_point(b), P.die_face(part, s.get("in_face", "W")),
                           P.die_face(part, s.get("out_face", "E")))
            k = (P.parts[part]["type"], slot)
            geo[k] = max(geo[k], C.plen(seg))
    bits = {(c["type"], c["slot"]): c for c in ft_reach.resize(copy.deepcopy(raw), REACH, 1.0, macrofree_only=False)}
    out = []
    for tn, t in raw["partition_types"].items():
        for s in t.get("ft_slots", []):
            k0 = int(s.get("stations", 1))
            key = (tn, s["name"])
            kb = bits[key]["stations"][1] if key in bits else k0
            k1 = max(k0, need(geo.get(key, 0.0)), kb)
            if codex is not None and tn in codex:
                assert codex[tn][s["name"]] == k1, (key, codex[tn][s["name"]], k1)
            s.pop("regs_um", None)
            if k1 != k0:
                s["stations"] = k1
                out.append(dict(type=tn, slot=s["name"], stations=[k0, k1], route_um=round(geo.get(key, 0.0), 1),
                                worst_bit_um=bits[key]["worst_bit_route_um"] if key in bits else None))
    return out


def core_boxes(t):
    out = []
    for c in t.get("hard_cores") or []:
        (ox, oy), (w, h) = c["origin_um"], c["outline_um"]
        dx, dy = c.get("track_offset_um", [0.0, 0.0])
        out.append((ox + dx - CLEAR, oy + dy - CLEAR, ox + dx + w + CLEAR, oy + dy + h + CLEAR))
    return out


def in_core(p, bx):
    return any(b[0] < p[0] < b[2] and b[1] < p[1] < b[3] for b in bx)


def split_leg(p, q, n, bx):
    """n points splitting p -> q evenly on an L (corner (q.x, p.y) or (p.x, q.y)), none in a core box."""
    best = None
    for corner in ((q[0], p[1]), (p[0], q[1])):
        pts = [p, corner, q]
        L = C.plen(pts)
        new = [tuple(round(v, 3) for v in C.point_at(pts, L * (i + 1) / (n + 1))) for i in range(n)]
        bad = sum(in_core(r, bx) for r in new)
        if best is None or bad < best[0]:
            best = (bad, new)
    return best


def respace_internal(raw):
    rep = []
    depth = {}                                   # (type, bus) -> (old depth, new depth)
    for tn, t in raw["partition_types"].items():
        ist = t.get("internal_stations") or []
        if not ist:
            continue
        bx = core_boxes(t)
        per_bus = defaultdict(list)
        for e in ist:
            pts = [tuple(e["from_um"])] + [tuple(r) for r in e["regs_um"]] + [tuple(e["to_um"])]
            if max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])) <= REACH + EPS:
                e["_new"], e["_in_core"] = pts, 0
                per_bus[e.get("conn")].append(e)
                continue
            # (a) the existing station path (every leg an L, corner off the cores) re-spaced evenly: ceil(L/405)-1
            path = [pts[0]]
            for p, q in zip(pts, pts[1:]):
                if abs(p[0] - q[0]) > EPS and abs(p[1] - q[1]) > EPS:
                    c1, c2 = (q[0], p[1]), (p[0], q[1])
                    path.append(c1 if not in_core(c1, bx) or in_core(c2, bx) else c2)
                path.append(q)
            L = C.plen(path)
            n = need(L) - 1
            new = [pts[0]] + [tuple(round(v, 3) for v in C.point_at(path, L * (i + 1) / (n + 1))) for i in range(n)] \
                + [pts[-1]]
            in_c = sum(in_core(r, bx) for r in new[1:-1])
            if in_c:                            # (b) fallback: split only the legs over the reach
                new, in_c = [pts[0]], 0
                for p, q in zip(pts, pts[1:]):
                    h = abs(p[0] - q[0]) + abs(p[1] - q[1])
                    if h > REACH + EPS:
                        bad, mid = split_leg(p, q, need(h) - 1, bx)
                        in_c += bad
                        new.extend(mid)
                    new.append(q)
            e["_new"] = new
            e["_in_core"] = in_c
            per_bus[e.get("conn")].append(e)
        for conn, es in per_bus.items():
            old = max(len(e["regs_um"]) for e in es)
            nd = max(len(e["_new"]) - 2 for e in es)
            for e in es:                        # pad to one depth per bus: split the largest hop at its L midpoint
                while len(e["_new"]) - 2 < nd:
                    pts = e["_new"]
                    j = max(range(len(pts) - 1), key=lambda i: abs(pts[i][0] - pts[i + 1][0]) + abs(pts[i][1] - pts[i + 1][1]))
                    _, mid = split_leg(pts[j], pts[j + 1], 1, bx)
                    e["_new"] = pts[:j + 1] + mid + pts[j + 1:]
                regs = [list(r) for r in e["_new"][1:-1]]
                hop = max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(e["_new"], e["_new"][1:]))
                if regs != e["regs_um"]:
                    e["regs_um"] = regs
                    e["note"] = (e.get("note", "") + f" | v3.9 (KV-405): {len(regs)} stations, hop {hop:.0f} <= "
                                 f"{REACH:g} (ruling 9.4)")
                rep.append(dict(type=tn, conn=conn, stations=[old, nd], max_hop_um=round(hop, 1),
                                in_core=e["_in_core"]))
                del e["_new"], e["_in_core"]
            if nd != old and conn and conn.startswith("bus:"):
                depth[(tn, conn[4:])] = (old, nd)
    # lanes ending on / starting from those (partition, bus) pairs
    ptype = {p["name"]: p["type"] for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    lanes = {}
    for ln in raw["lanes"]:
        a, b = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        d = 0
        for end in (a["src"], b["dst"]):
            k = (ptype.get(end["part"]), end["bus"])
            if k in depth:
                d += depth[k][1] - depth[k][0]
        if d:
            ln["fixed_cycles"] = int(ln.get("fixed_cycles", 0)) + d
            ln["note"] = ln.get("note", "") + f" | v3.9 (KV-405) +{d} internal stations at <= {REACH:g} um"
            lanes[ln["id"]] = d
    return rep, {f"{k[0]}:{k[1]}": v for k, v in depth.items()}, lanes


def phy_reset_tap(raw):
    out = {}
    for tn in PHY_TYPES:
        t = raw["partition_types"][tn]
        W, H = t["outline_um"]
        old = list(t["reset"]["tap_um"])
        t["reset"]["tap_um"] = [round(W - PHY_TAP_INSET, 3), old[1]]
        out[tn] = dict(old=old, new=t["reset"]["tap_um"])
    return out


def reset_wavefront(raw):
    old = raw["reset"].get("release")
    raw["reset"]["release"] = "wavefront"
    return dict(old=old, new="wavefront")


AHUB_NEW = [604.8, 440.64]


def ahub_r2(raw):
    c = next(c for c in raw["partition_types"]["kv3_hub_C"]["hard_cores"] if c["inst"] == "ahub")
    old = dict(origin_um=list(c["origin_um"]), outline_um=list(c["outline_um"]))
    if c["outline_um"] != AHUB_NEW:
        se_x = c["origin_um"][0] + c["outline_um"][0]
        c["origin_um"] = [round(se_x - AHUB_NEW[0], 3), c["origin_um"][1]]
        c["outline_um"] = list(AHUB_NEW)
        c["note"] = c.get("note", "") + (" | v3.9 (KV-405): r2 macro-composed shrink 734.4 x 540 -> 604.8 x 440.64, S-E "
                                         "corner fixed (KV-CORES ahub_fp_proposal r2 @666f376ad; GEOM-REVIEW PASS-COND)")
    return dict(old=old, new=dict(origin_um=c["origin_um"], outline_um=c["outline_um"]))


def main():
    a = sys.argv[1:]
    raw = json.load(open(a[0]))
    codex = None
    if "--codex" in a:
        cx = json.load(open(a[a.index("--codex") + 1]))
        codex = {"kv3_hub_Ei": {s["name"]: s["stations"] for s in cx["partition_types"]["kv3_hub_Ei"]["ft_slots"]}}
    rep = dict(schema="opentallas.kv405.post_v39.v1", reach_um=REACH)
    rep["die_old"] = die_level(raw)
    rep["reset"] = reset_wavefront(raw)
    rep["ahub_r2"] = ahub_r2(raw)
    rep["slots"] = size_slots(raw, codex)
    rep["internal"], rep["internal_depth"], rep["internal_lanes"] = respace_internal(raw)
    rep["phy_reset_tap"] = phy_reset_tap(raw)
    raw["note"] = raw.get("note", "") + (
        " | v3.9 (KV-405 10-24, owner dec. 12/17, rulings 9.3/9.4): signals <= M7 (no ft_reserved), die.reach_um 405, "
        f"ft stations / hops / internal stations <= {REACH:g} um exactly ({len(rep['slots'])} slots resized, "
        "ft_channel_regs re-derives core-free sites); reset.release wavefront, kv3_phy reset taps at the E face (toward "
        "pc); qkd_ahub r2 604.8 x 440.64; ectlk / ahub clock entries centred (core_pins_v39.py)")
    if "--report" in a:
        Path(a[a.index("--report") + 1]).write_text(json.dumps(rep, indent=1))
    sys.stderr.write(f"post_v39: {len(rep['slots'])} slots resized, internal depth changes {rep['internal_depth']}, "
                     f"{len(rep['internal_lanes'])} lanes +internal\n")
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
