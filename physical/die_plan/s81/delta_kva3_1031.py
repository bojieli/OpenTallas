#!/usr/bin/env python3
"""DIE-S81-46 10-31: kv_leaf__t2 three-slot (a3) plan event (COORD 21:43 else-branch, COORD 22:3x ruling (2): (c) closed,
a3 and the pool split estimated first; the pool split lost on area (77-87 % vs a3 63-73 %), so a3 is built).

Geometry on a COPY of the plan of record (inputs are never edited):
  1. kv_leaf__t2 (s_3N_L0) 1442.88 -> 4328.64 x 1226.88, origin (13089.6, 16053.12): it takes the s_2N_L0 and s_4N_L0
     slots.  Its own type frame shifts +1442.88 in x (every point / rect / N-S window); the through ft slots of
     leaf__t27 (R0 at the same origin, frame unchanged) become ft10..ft14 and those of leaf__t42 (MY at x+2885.76,
     mirrored: x -> 4328.64 - x, cell sites -> 4328.64 - x - cell_w, bit order flipped) become ft15..ft22; every port
     of those slots is re-targeted to s_3N_L0 with the same die window (no E/W or internal ports exist between the
     three slots: CHECKED on the plan of record).
  2. leaf__t27 (s_2N_L0) -> free cell F1 (11646.72, 23414.4) MX; leaf__t42 (s_4N_L0) -> free cell F2 (17418.24,
     22187.52) MX: their buses leafdn_i0 / leafup_o0 (type N face) face die S.  Their four slice lanes
     dn/up_s_2N_L0 and dn/up_s_4N_L0 (the direct C<->L0 ports) are re-built as hop chains with
     tools/die_plan/lane_add.Builder.build_one (free windows on every shared edge, stations = ceil(route/ft max),
     macro-free station re-site), on fixed chains through single-instance types only (the slice-2N column is full at
     s_2N_C|s_2N_L1, 10 um free vs 211 um needed; s_4N_L4's type has 2 instances):
        t27: s_2N_C, s_1N_C, s_1N_L1, s_1N_L3, s_1N_L4, s_1N_x06, s_2N_L0@F1
        t42: s_4N_C, s_4N_L1, s_4N_L3, s_5N_L3, s_5N_L4, s_4N_L0@F2
     The lane ids, latency params and the end bus names (C leafdn_o4 / leafup_i4, leaf leafdn_i0 / leafup_o0) are
     kept; only their face / window / layers / order change.
  3. landing regions: s_3N_L0 box = the a3 box; the moved leaves get F1 / F2 boxes.  Variant TAG (default) = a moved
     leaf takes the tag of the partition its chain enters from (s_1N_x06 / s_5N_L4: no crossing on the last hop);
     variant TRAVEL = the tags travel.  The crossing table is re-derived from the tags.
Then the WS3 splice of delta_ws3_1031 (unmodified functions): clock_landing_plan.compose on BASE and NEW, three-way
merge, post rules, restation, delta_alltap_1030 + delta_alltap_coll_1030 on every changed type, gen.py latency.

usage (repo root): delta_kva3_1031.py --variant TAG|TRAVEL --out DIR [--base DIR] [--plan P] [--sidecar S]
  [--geometry-only]
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402


def load_mod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m                      # multiprocessing pickles DW._compose by module reference
    sp.loader.exec_module(m)
    return m


DW = load_mod("delta_ws3_1031", HERE / "delta_ws3_1031.py")
import lane_add as LA
import check as C  # noqa: E402

W, H = 1442.88, 1226.88
X2, Y0 = 13089.6, 16053.12
F1, F2 = [11646.72, 23414.4], [17418.24, 22187.52]
T2, T27, T42 = "ot_s81sl_kv_leaf__t2", "ot_s81sl_leaf__t27", "ot_s81sl_leaf__t42"
CHAINS = {
    "dn_s_2N_L0": ["s_2N_C", "s_1N_C", "s_1N_L1", "s_1N_L3", "s_1N_L4", "s_1N_x06", "s_2N_L0"],
    "up_s_2N_L0": ["s_2N_L0", "s_1N_x06", "s_1N_L4", "s_1N_L3", "s_1N_L1", "s_1N_C", "s_2N_C"],
    "dn_s_4N_L0": ["s_4N_C", "s_4N_L1", "s_4N_L3", "s_5N_L3", "s_5N_L4", "s_4N_L0"],
    "up_s_4N_L0": ["s_4N_L0", "s_5N_L4", "s_5N_L3", "s_4N_L3", "s_4N_L1", "s_4N_C"],
}
ENTRY = {"s_2N_L0": "s_1N_x06", "s_4N_L0": "s_5N_L4"}
# preferred N-S window centre (fraction of the column width from its W edge), tried in order until the macro-free
# station re-site of lane_add succeeds (DIE-S81-46 probe: x 12530/12700 FAIL, 12900/12950 OK on the 1N column)
PREF_FRAC = (0.87, 0.91, 0.80, 0.75, 0.70, 0.95, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10)

POINT = {"xy", "xy_um", "pin_xy_um", "tap_um", "root", "pin_um", "from_um", "to_um", "origin_um"}
RECT = {"rect_um"}
PTLIST = {"outs", "regs_um"}
ROWS = {"sink_sites_um"}
SKIP = {"outline_um", "track_offset_um", "bit_site_cell_um", "window_um", "in_window_um", "out_window_um"}


def r6(v):
    return round(float(v), 6)


def shift_x(o, dx, path="", unknown=None):
    """shift every type-frame x coordinate of o by dx (R0 translation); N/S windows handled by the caller."""
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}/{k}"
            if k in SKIP:
                continue
            if k in POINT and isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
                o[k] = [r6(v[0] + dx), v[1]]
            elif k in RECT and isinstance(v, list) and len(v) == 4:
                o[k] = [r6(v[0] + dx), v[1], r6(v[2] + dx), v[3]]
            elif k in PTLIST and isinstance(v, list):
                o[k] = [[r6(q[0] + dx), q[1]] for q in v]
            elif k in ROWS and isinstance(v, list):
                o[k] = [[r6(q[0] + dx)] + list(q[1:]) for q in v]
            elif k == "bit_sites_um":
                o[k] = [[[r6(c[0] + dx), c[1]] for c in st] for st in v]
            else:
                if isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v) and unknown is not None:
                    unknown.add(p)
                shift_x(v, dx, p, unknown)
    elif isinstance(o, list):
        for x in o:
            shift_x(x, dx, path + "[]", unknown)


def shift_windows(t, dx):
    for b in t.get("buses", []):
        if b["face"] in "NS":
            b["window_um"] = [r6(b["window_um"][0] + dx), r6(b["window_um"][1] + dx)]
    for s in t.get("ft_slots", []):
        for f, k in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s[f] in "NS":
                s[k] = [r6(s[k][0] + dx), r6(s[k][1] + dx)]


FLIP = {"lsb_low": "lsb_high", "lsb_high": "lsb_low"}


def mirror_slot(s, ext):
    """MY-instance slot -> R0 frame of the merged type: x -> ext - x."""
    s = copy.deepcopy(s)
    for f, k in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
        assert s[f] in "NS", (s["name"], s[f])
        a, b = s[k]
        s[k] = [r6(ext - b), r6(ext - a)]
    for k in ("order", "in_order", "out_order"):
        if k in s:
            s[k] = FLIP[s[k]]
    if "regs_um" in s:
        s["regs_um"] = [[r6(ext - q[0]), q[1]] for q in s["regs_um"]]
    if "bit_sites_um" in s:
        cw = float(s["bit_site_cell_um"][0])
        s["bit_sites_um"] = [[[r6(ext - c[0] - cw), c[1]] for c in st] for st in s["bit_sites_um"]]
    return s


def resite_seq(self, chain, slots, start, end):
    """fallback for lane_add.Builder.resite on an L-shaped chain (its exact-count solve back-traces to the straight
    start-end line, which leaves the turn partitions): partition by partition, station_resite.route from the previous
    real register (or the lane start) to the partition's exit face point with that partition's own count (+1 or +2
    if it cannot), FF homes off every core/macro + halo; every hop <= reach (the next partition starts from the last
    real register).  Returns per-slot die-frame regs, the station counts may grow (reported by the caller)."""
    import numpy as np
    import station_resite as SR
    P, G, Hh = self.P, SR.G, SR.HALO
    got = self._resite_orig(chain, slots, start, end)
    if got is not None:
        return got
    out, cur = [], tuple(start)
    for i, sl in enumerate(slots):
        p = sl[0]
        x0, y0, x1, y1 = P.rect(p)
        X0, Y0 = x0 - 2 * self.reach, y0 - 2 * self.reach
        nx, ny = int((x1 - X0 + 2 * self.reach) / G) + 2, int((y1 - Y0 + 2 * self.reach) / G) + 2
        xs, ys = X0 + np.arange(nx) * G, Y0 + np.arange(ny) * G
        m = (xs[:, None] > x0 + Hh) & (xs[:, None] < x1 - Hh) & (ys[None, :] > y0 + Hh) & (ys[None, :] < y1 - Hh)
        for bx0, by0, bx1, by1 in S.placed_macro_boxes(P.ptype(p), halo=Hh).values():
            c0, c1 = P.to_die(p, (bx0, by0)), P.to_die(p, (bx1, by1))
            ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
            m &= ~((xs[:, None] > ux0 - 1e-6) & (xs[:, None] < ux1 + 1e-6) & (ys[None, :] > uy0 - 1e-6)
                   & (ys[None, :] < uy1 + 1e-6))
        b = tuple(end) if i == len(slots) - 1 else self.face_pt(P, p, sl[5], sl[6])
        regs = None
        for k in (sl[8], sl[8] + 1, sl[8] + 2):
            SR.G = G
            r = SR.route(m, (cur[0] - X0, cur[1] - Y0), (b[0] - X0, b[1] - Y0), k, self.reach)
            if r is not None and sl[10] / len(r) <= self.smax + 1e-6:
                regs = [(round(x + X0, 4), round(y + Y0, 4)) for x, y in r]
                break
        if regs is None:
            return None
        out.append(regs)
        cur = regs[-1]
    return out


LA.Builder._resite_orig = LA.Builder.resite
LA.Builder.resite = resite_seq


def fco_rule(plan, changed, log):
    """every plan-of-record type whose forwarded landing clock output is sourced from a tap port (source_clock_port
    != clk) carries landing_contract.forwarded_clock_only_inputs = true (186/186 in plan 1559; clock_landings EMIT
    fails closed without it).  DW.post_rules copies the key only from the POR type, so a type that gains its first
    tap-sourced forwarded output in this delta (leaf__t54__cl706d9749 on dn_s_2N_L0) gets it here."""
    for tn in changed:
        lc = (plan["partition_types"][tn].get("clock") or {}).get("landing_contract") or {}
        if lc.get("forwarded_clock_only_inputs") is True:
            continue
        if any(q.get("kind") == "clock" and q.get("dir") == "out" and q.get("source_clock_port", "clk") != "clk"
               for q in lc.get("pins", [])):
            lc["forwarded_clock_only_inputs"] = True
            log.append(f"{tn}: forwarded_clock_only_inputs true (tap-sourced forwarded clock output, POR class rule)")


def boot_law(side, log):
    """the stored ready_at_glue_max_cycles follows the plan-of-record law (prepare_h2_2249.py, re-checked by
    delta_alltap_coll_1030): deadline(p) = max(rel + 21, child deadlines + (21 seam | STATUS_FACE_CYCLES)) + local depth.
    compose writes its own figure (BASE 518 vs POR 522 on the unchanged plan), so after the 3-way merge the budget
    is re-derived with the POR law from the merged parents/depths."""
    import clock_landing_plan as CLP
    col = side["collector"]
    bb, ct, parts = col["boot_budget"], col["types"], col["parts"]
    rel, dl = bb["raw_reset_release_max_cycles"], {}

    def deadline(pn):
        if pn not in dl:
            inf = ct[parts[pn]["type"]]
            ch = [deadline(c["part"]) + (21 if c["seam"] else CLP.STATUS_FACE_CYCLES) for c in inf["children"]]
            dl[pn] = max([rel + 21] + ch) + bb["local_registered_depths"][pn]
        return dl[pn]
    v = deadline(col["root"])
    log.append(f"boot budget ready_at_glue_max_cycles {bb['ready_at_glue_max_cycles']} (merge) -> {v} (POR law)")
    bb["ready_at_glue_max_cycles"] = v


def geometry(por, table, variant, log):
    raw = copy.deepcopy(por)
    T = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    cnt = {}
    for p in raw["partitions"]:
        cnt[p["type"]] = cnt.get(p["type"], 0) + 1
    for n, tn, o in (("s_3N_L0", T2, "R0"), ("s_2N_L0", T27, "R0"), ("s_4N_L0", T42, "MY")):
        assert parts[n]["type"] == tn and cnt[tn] == 1 and parts[n].get("orient", "R0") == o, (n, tn)
    assert parts["s_2N_L0"]["origin_um"] == [X2, Y0] and parts["s_3N_L0"]["origin_um"] == [X2 + W, Y0]
    assert parts["s_4N_L0"]["origin_um"] == [X2 + 2 * W, Y0]
    three = {"s_2N_L0", "s_3N_L0", "s_4N_L0"}
    for pr in raw["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        assert not (a in three and b in three), ("internal port", pr["id"])
    import clock_landing_plan as CLP
    CLP.clear_generated_landing_infra(raw)        # compose clears it too; the lane builder needs no stale landings
    T = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    t2, t27, t42 = T[T2], T[T27], T[T42]
    # ------------------------------------------------------------ 1. t2 frame +W, outline 3W
    unknown = set()
    shift_windows(t2, W)
    shift_x(t2, W, T2, unknown)
    assert not unknown, ("unhandled numeric keys", sorted(unknown))
    t2["outline_um"] = [r6(3 * W), H]
    parts["s_3N_L0"]["origin_um"] = [X2, Y0]
    log.append(f"{T2}: outline -> {t2['outline_um']}, frame +{W} (points/rects/NS windows), s_3N_L0 origin -> {[X2, Y0]}")
    ren = {}
    for s in t27["ft_slots"]:
        n = "ft%d" % (10 + int(s["name"][2:]))
        ns = copy.deepcopy(s)
        ns["name"] = n
        t2["ft_slots"].append(ns)
        ren[("s_2N_L0", s["name"])] = n
    for s in t42["ft_slots"]:
        n = "ft%d" % (15 + int(s["name"][2:]))
        ns = mirror_slot(s, 3 * W)
        ns["name"] = n
        t2["ft_slots"].append(ns)
        ren[("s_4N_L0", s["name"])] = n
    log.append(f"{T2}: + {len(t27['ft_slots'])} slots of {T27} (ft10..) + {len(t42['ft_slots'])} slots of {T42} "
               "(ft15.., mirrored)")
    t27["ft_slots"], t42["ft_slots"] = [], []
    nre = 0
    for pr in raw["ports"]:
        for e in ("src", "dst"):
            q = pr[e]
            if q["part"] in ("s_2N_L0", "s_4N_L0") and q["bus"].startswith("ft"):
                sl, io = q["bus"].rsplit("_", 1)
                q["part"], q["bus"] = "s_3N_L0", ren[(pr[e]["part"], sl)] + "_" + io
                nre += 1
    log.append(f"{nre} slot port ends re-targeted to s_3N_L0")
    # ------------------------------------------------------------ 2. move the two leaves, re-tap later
    for n, xy in (("s_2N_L0", F1), ("s_4N_L0", F2)):
        log.append(f"{n} ({parts[n]['type']}) {parts[n]['origin_um']} {parts[n].get('orient', 'R0')} -> {xy} MX")
        parts[n]["origin_um"] = list(xy)
        parts[n]["orient"] = "MX"
    # ------------------------------------------------------------ 3. landing regions (before the lane build: tags)
    tab = copy.deepcopy(table)
    reg = {}
    for r in tab["regions"]:
        for q in r["parts"]:
            reg[q] = r
    reg["s_3N_L0"]["box_um"] = [X2, Y0, r6(X2 + 3 * W), r6(Y0 + H)]
    for n, xy in (("s_2N_L0", F1), ("s_4N_L0", F2)):
        reg[n]["box_um"] = [xy[0], xy[1], r6(xy[0] + W), r6(xy[1] + H)]
        if variant == "TAG":
            log.append(f"TAG: region k={reg[n]['k']} ({n}) tag {reg[n]['tag']} -> {reg[ENTRY[n]]['tag']} ({ENTRY[n]})")
            reg[n]["tag"] = reg[ENTRY[n]]["tag"]
        else:
            log.append(f"TRAVEL: {n} keeps tag {reg[n]['tag']}")
    # ------------------------------------------------------------ 4. re-build the four leaf lanes
    lanes = {l["id"]: l for l in raw["lanes"]}
    ports = {p["id"]: p for p in raw["ports"]}
    old = {}
    for lid in CHAINS:
        ln = lanes[lid]
        assert len(ln["ports"]) == 1, lid
        pr = ports[ln["ports"][0]]
        old[lid] = dict(lane=copy.deepcopy(ln), port=copy.deepcopy(pr), lat=copy.deepcopy(raw["latency"]["lanes"][lid]))
        # the moved leaf keeps its bus where its cores expect it: same type-frame window centre as the plan of record
        # (MX keeps type x; G0C internal_station flags core bundle -> bus > 405 um otherwise, 442-777 um in g2)
        leaf = pr["dst"]["part"] if lid.startswith("dn_") else pr["src"]["part"]
        lb = pr["dst"]["bus"] if lid.startswith("dn_") else pr["src"]["bus"]
        lp = parts[leaf]
        assert lp["orient"] == "MX" and leaf in ENTRY, (lid, leaf, lp.get("orient"))
        bw = next(b for b in T[lp["type"]]["buses"] if b["name"] == lb)["window_um"]
        old[lid]["leaf_edge"] = (leaf, round(lp["origin_um"][0] + (bw[0] + bw[1]) / 2, 4))
        raw["ports"].remove(pr)
        raw["lanes"].remove(ln)
        del raw["latency"]["lanes"][lid]
        for e in ("src", "dst"):
            t = T[parts[pr[e]["part"]]["type"]]
            t["buses"] = [b for b in t["buses"] if b["name"] != pr[e]["bus"]]
    B = LA.Builder(raw, near_um=1e9, max_hops=12, require_cycle_match=False)
    P0 = S.Plan(copy.deepcopy(raw))
    built = {}
    for lid, chain in CHAINS.items():
        pr = old[lid]["port"]
        a, b = pr["src"]["part"], pr["dst"]["part"]
        assert chain[0] == a and chain[-1] == b, (lid, chain, a, b)
        B.new_id = (lambda x, y, z=0, _l=lid: _l)
        r, tried = None, []
        for fe in (0.5, 0.25, 0.75, 0.1, 0.9):
            for f in PREF_FRAC:
                real_alloc = B.alloc

                def alloc(u, v, bits, prefer=None, _f=f, _fe=fe, _ra=real_alloc, _le=old[lid]["leaf_edge"]):
                    df, lo, hi = LA.shared_edge(B.P, u, v)
                    if _le[0] in (u, v):
                        return _ra(u, v, bits, prefer=_le[1])
                    return _ra(u, v, bits, prefer=lo + (_f if df in "NS" else _fe) * (hi - lo))
                B.alloc = alloc
                snap = copy.deepcopy({k: v for k, v in B.__dict__.items() if k != "alloc"})
                r = B.build_one(a, b, int(pr["width"]), chain, "path", None, record=False)
                B.alloc = real_alloc
                why = B._why if r is None else "OK"
                if r is not None:
                    # G0C hops (check.lane_pin_hops) route every FF-to-FF hop through the slot pins; lane_add's own
                    # test is pin-free Manhattan, so an L-turn slot can pass here and fail G0C (613 um at s_1N_C)
                    Pt = S.Plan(copy.deepcopy(B.raw))
                    _, regs, _ = C.lane_geometry(Pt, lid)
                    hw = max(C.lane_pin_hops(Pt, lid, regs) or [0.0])
                    if hw > S.SIGNAL_REACH_UM + 1e-6:
                        why = f"pin hop {hw:.0f}"
                        B.__dict__.update(snap)
                        r = None
                tried.append((f, fe, why))
                if r is not None:
                    break
            if r is not None:
                break
        if r is None:
            raise SystemExit(f"{lid}: build failed: {tried}")
        log.append(f"{lid}: window preference (NS frac, EW frac) tries {tried}")
        built[lid] = r
        raw = B.raw
        T = raw["partition_types"]
        parts = {p["name"]: p for p in raw["partitions"]}
        # end bus names / lane record / latency param of the plan of record
        ln = next(l for l in raw["lanes"] if l["id"] == lid)
        keep = {k: v for k, v in old[lid]["lane"].items() if k != "ports"}
        ln.clear()
        ln.update(keep)
        ln["ports"] = [f"{lid}_{i}" for i in range(len(chain) - 1)]
        pp = [p for p in raw["ports"] if p["id"] in ln["ports"]]
        for e, nb in (("src", f"{lid}_o"), ("dst", f"{lid}_i")):
            end = pp[0] if e == "src" else pp[-1]
            t = T[parts[end[e]["part"]]["type"]]
            bus = next(x for x in t["buses"] if x["name"] == nb)
            bus["name"] = pr[e]["bus"]
            end[e]["bus"] = pr[e]["bus"]
        for p in pp:
            p["order"] = "lsb_low"
        lat = raw["latency"]["lanes"][lid]
        lat["param"] = old[lid]["lat"]["param"]
        B.P = S.Plan(raw)
        log.append(f"{lid}: {' -> '.join(chain)}; cycles {old[lid]['lat']['cycles']} -> {r['cycles']} "
                   f"(stations {r['stations']}, landing {r.get('clock_landing')}); crossings "
                   + ", ".join(f"{x['part']}/{x['slot']} k={x['stations']} {x['route_um']}um" for x in r["crossings"]))
    # ------------------------------------------------------------ 5. crossing table from the tags
    tag = {}
    for r in tab["regions"]:
        for q in r["parts"]:
            tag[q] = r["tag"]
    P = S.Plan(raw)
    lane_of = {pid: lid for lid, ln in P.lanes.items() for pid in ln["ports"]}
    rows = {}
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a in tag and b in tag and tag[a] != tag[b]:
            rows[pid] = dict(port=pid, lane=lane_of.get(pid), src=a, dst=b, src_region=tag[a], dst_region=tag[b],
                             width=pr["width"], kind=pr.get("kind", "data"), added_cycles=tab["added_cycles_per_crossing"])
    oldrows = {r["port"]: r for r in table["ports"]}
    order = [p for p in oldrows if p in rows] + sorted(p for p in rows if p not in oldrows)
    changed = sorted(p for p in rows if p in oldrows and rows[p] != oldrows[p])
    tab["ports"] = [rows[p] for p in order]
    tab["crossings"] = len(rows)
    tab["bits"] = sum(r["width"] for r in rows.values())
    tab["lanes"] = len({r["lane"] for r in rows.values()})
    by = dict(ports=len(rows), bits=tab["bits"])
    tab["by_class_pair"] = {"std->std": by}
    log.append(f"landing table: crossings {table['crossings']} -> {tab['crossings']} (removed "
               f"{sorted(set(oldrows) - set(rows))[:12]}, added {sorted(set(rows) - set(oldrows))[:24]}, "
               f"changed {changed[:12]})")
    # ------------------------------------------------------------ 6. re-tap: grid on every type this event touches
    touched = sorted({T2, T27, T42} | {parts[c]["type"] for ch in CHAINS.values() for c in ch})
    for tn in touched:
        ck = T[tn]["clock"]
        ck["tap_mode"] = "grid"
        ck.pop("added_taps", None)
        ck.pop("sink_sites_um", None)
    log.append(f"re-tap (grid, alltap after compose) {touched}")
    return raw, tab, dict(built=built, touched=touched)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", choices=("TAG", "TRAVEL"), default="TAG")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base")
    ap.add_argument("--plan", default=str(HERE / "plan_h2_2249.json"))
    ap.add_argument("--sidecar", default=str(HERE / "h2_2249/landed_sidecar_h2.json"))
    ap.add_argument("--geometry-only", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="reuse OUT/NEW and OUT/BASE composes (geometry is deterministic)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    por_text = Path(a.plan).read_text()
    side_text = Path(a.sidecar).read_text()
    por, side = json.loads(por_text), json.loads(side_text)
    table = {k: v for k, v in side.items() if k != "collector"}
    log, conflicts = [], []
    geom, tab, grec = geometry(por, table, a.variant, log)
    (out / "geom.json").write_text(json.dumps(geom, separators=(",", ":")) + "\n")
    (out / "table.json").write_text(json.dumps(tab, separators=(",", ":")) + "\n")
    (out / "por_table.json").write_text(json.dumps(table, separators=(",", ":")) + "\n")
    (out / "geom_log.json").write_text(json.dumps(dict(log=log, built=grec["built"], touched=grec["touched"]), indent=1) + "\n")
    print("\n".join(map(str, log)))
    if a.geometry_only:
        return
    RETAP = tuple(grec["touched"])
    DW.RELAX = set(RETAP)
    jobs = [(str(out / "geom.json"), str(out / "table.json"), str(out / "NEW"))]
    bdir = Path(a.base) if a.base else out / "BASE"
    if not (bdir / "plan.json").exists():
        jobs.append((a.plan, str(out / "por_table.json"), str(bdir)))
    if a.reuse and (out / "NEW/plan.json").exists():
        jobs = [j for j in jobs if not (Path(j[2]) / "plan.json").exists()]
        assert json.loads((out / "NEW/geom_sha.json").read_text()) == hashlib.sha256((out / "geom.json").read_bytes()).hexdigest() \
            if (out / "NEW/geom_sha.json").exists() else True
    secs = []
    if jobs:
        with mp.get_context("fork").Pool(len(jobs)) as pool:
            secs = pool.map(DW._compose, jobs)
    (out / "NEW/geom_sha.json").write_text(json.dumps(hashlib.sha256((out / "geom.json").read_bytes()).hexdigest()) + "\n")
    log.append(f"compose secs {secs}")
    B, Bs = json.loads((bdir / "plan.json").read_text()), json.loads((bdir / "sidecar.json").read_text())
    V, Vs = json.loads((out / "NEW/plan.json").read_text()), json.loads((out / "NEW/sidecar.json").read_text())
    changed = sorted(tn for tn in V["partition_types"] if V["partition_types"][tn] != B["partition_types"].get(tn))
    inst = {}
    for p in V["partitions"]:
        inst.setdefault(p["type"], []).append(p["name"])
    multi = {tn: inst.get(tn) for tn in changed if len(inst.get(tn, [])) != 1}
    log.append(f"compose changed types {changed}; multi-instance {multi}")
    plan = DW.merge3(por, B, V, "", conflicts)
    nside = DW.merge3(side, Bs, Vs, "", conflicts)
    boot_law(nside, log)
    DW.post_rules(plan, nside, por, changed, log)
    fco_rule(plan, changed, log)
    DW.restation(plan, a.plan, changed, log)
    plan_p = out / "plan_h2_2249.json"
    side_p = out / "landed_sidecar_h2.json"
    plan_p.write_text(DW.write_plan(por_text, por, plan, log))
    side_p.write_text(json.dumps(nside, separators=(",", ":")) + "\n")
    retap = sorted(set(RETAP) | set(changed))
    rx = "^(" + "|".join(retap) + ")$"
    r = subprocess.run([sys.executable, str(HERE / "delta_alltap_1030.py"), str(plan_p), str(out / "plan_tap.json"),
                        str(out / "alltap_report.json"), "--types", rx], cwd=str(ROOT), capture_output=True, text=True)
    log.append(f"delta_alltap_1030 rc {r.returncode}: {(r.stdout + r.stderr)[-400:]}")
    if r.returncode:
        (out / "receipt.json").write_text(json.dumps(dict(log=log, conflicts=conflicts), indent=1, default=str) + "\n")
        raise SystemExit("alltap failed")
    os.replace(out / "plan_tap.json", plan_p)
    env = dict(os.environ, TYPES_RE=rx)
    r = subprocess.run([sys.executable, str(HERE / "delta_alltap_coll_1030.py"), str(plan_p), str(side_p),
                        str(out / "alltap_coll_report.json")], cwd=str(ROOT), capture_output=True, text=True, env=env)
    log.append(f"delta_alltap_coll_1030 rc {r.returncode}: {(r.stdout + r.stderr)[-400:]}")
    if r.returncode:
        (out / "receipt.json").write_text(json.dumps(dict(log=log, conflicts=conflicts), indent=1, default=str) + "\n")
        raise SystemExit("alltap_coll failed")
    plan = json.loads(plan_p.read_text())
    lat_copy = out / "lat_plan.json"
    lat_copy.write_text(plan_p.read_text())
    r = subprocess.run([sys.executable, str(ROOT / "tools/die_plan/gen.py"), "latency", str(lat_copy), "--inplace",
                        "--out", str(out / "lat")], cwd=str(ROOT), capture_output=True, text=True)
    log.append(f"gen.py latency rc {r.returncode}: {(r.stdout + r.stderr)[-300:]}")
    if r.returncode:
        raise SystemExit("latency failed")
    lat = json.loads(lat_copy.read_text())["latency"]
    lat_copy.unlink()
    if lat != plan["latency"]:
        new = copy.deepcopy(plan)
        new["latency"] = lat
        plan_p.write_text(DW.write_plan(plan_p.read_text(), plan, new, log))
        plan = new
    c0 = {k: v["cycles"] for k, v in por["latency"]["lanes"].items()}
    c1 = {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}
    lane_changes = {k: dict(before=c0.get(k), after=c1.get(k)) for k in sorted(set(c0) | set(c1)) if c0.get(k) != c1.get(k)}
    final_side = json.loads(side_p.read_text())
    col = final_side["collector"]
    types_changed = sorted(tn for tn in plan["partition_types"] if plan["partition_types"][tn] != por["partition_types"].get(tn))
    sha = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()
    rec = dict(kind="S81_KVA3_1031", variant=a.variant, lane="DIE-S81-46",
               inputs=dict(plan=dict(path=a.plan, sha256=sha(por_text)), sidecar=dict(path=a.sidecar, sha256=sha(side_text))),
               outputs=dict(plan_sha256=sha(plan_p.read_bytes()), sidecar_sha256=sha(side_p.read_bytes())),
               compose_changed_types=changed, plan_changed_types=types_changed,
               other_top_level_changed=[k for k in plan if k != "partition_types" and plan[k] != por[k]],
               merge_conflicts=conflicts, built=grec["built"], lane_cycle_changes=lane_changes,
               lane_sum=dict(before=sum(c0.values()), after=sum(c1.values())),
               crossings=dict(before=side["crossings"], after=final_side["crossings"]),
               boot=dict(before=side["collector"]["boot_budget"]["ready_at_glue_max_cycles"],
                         after=col["boot_budget"]["ready_at_glue_max_cycles"]),
               placement_failures_new=[f for f in col["placement_failures"] if f["type"] in changed],
               log=log, secs=round(time.time() - t_start))
    (out / "receipt.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps({k: rec[k] for k in ("variant", "compose_changed_types", "crossings", "boot", "lane_sum",
                                          "placement_failures_new", "secs")}, indent=1, default=str))
    print("merge conflicts", len(conflicts), "lane cycle changes", len(lane_changes))


if __name__ == "__main__":
    main()
