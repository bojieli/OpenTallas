#!/usr/bin/env python3
"""SVC-YTRADE-1 (OPUS-FIX-S81-SVC-R9, COORD 11-23 ruling on the 3 EDGESTRIP-1-SVC NO-MOVE svc_hi types): a Y trade
inside each die column; the die and the column are unchanged.

For every svc_lo partition LO named with --lo (each sits under a svc_hi type with no N room for the 69.12 S strip):
  * LO shrinks at its N edge by G (outline H -G, origin unchanged).  Its cores, contents and interior are unchanged;
    the N-face points (on the N edge, or in the N strip at least G above the top core: edge clocks, collector relays,
    N-face stations) move -G with that face, so they keep their offset from it and stay out of the cores.
  * EVERY partition whose S face abuts LO's N face grows at its S edge by G: origin y -G, outline H +G and the whole
    type interior +G in the type frame (cores, contents, regs, taps, stations, ft bit sites, E/W bus/slot y windows,
    reset in_site).  Points anchored on the S face (within EDGE) stay with that face.  Die positions of the
    interiors do not move, so every S strip of a grown type grows by G.
  A LO is skipped (SKIP-NOT-NEEDED) when no abutter has a >=MIN_BITS S window with a core closer than STRIP.
  The abutters must cover LO's x span exactly and abut nothing else on their S face; every changed type must have one
  instance, and the orientations must keep type N = die N (R0/MY).  Die ports are unchanged: N/S seam windows are
  x ranges, and E/W windows keep their die y.  A port on an E/W face of LO that reaches above the new LO top is refused.

usage: svc_ytrade_row.py PLAN_IN --lo svc_0,svc_10,svc_14 [--grow 34.56] [--apply OUT] [--ops OPS] [--report REP]
"""
import argparse
import copy
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_rect_follow as RF  # noqa: E402  rect / tap-window followers (FAM-S81-SVC-OWN 11-24)

ap = argparse.ArgumentParser()
ap.add_argument("plan")
ap.add_argument("--lo", required=True)
ap.add_argument("--grow", type=float, default=34.56)
ap.add_argument("--edge", type=float, default=2.2)
ap.add_argument("--strip", type=float, default=69.12)
ap.add_argument("--core-margin", type=float, default=17.28)
ap.add_argument("--min-bits", type=int, default=256)
ap.add_argument("--apply")
ap.add_argument("--ops")
ap.add_argument("--report")
a = ap.parse_args()

R = lambda v: round(v, 4)
G = a.grow
P = json.load(open(a.plan))
T = P["partition_types"]
PL = P["partitions"]
PI = {p["name"]: i for i, p in enumerate(PL)}
NINST = Counter(p["type"] for p in PL)
NONPOINT = {"outline_um", "track_offset_um", "bit_site_cell_um", "window_um", "in_window_um", "out_window_um", "bits",
            "halo_um", "size_um", "pitch_um", "range", "span_um"}
SKIP_SUBTREES = {"buses", "dead_inputs", "relay_depth", "verilog_defines", "count_straps"}
WINKEYS = ("window_um", "in_window_um", "out_window_um")
problems = []


def box(n):
    p = PL[PI[n]]
    W, H = T[p["type"]]["outline_um"]
    x, y = p["origin_um"]
    return x, y, x + W, y + H


def is_pt(v):
    return isinstance(v, list) and len(v) == 2 and all(isinstance(z, (int, float)) and not isinstance(z, bool) for z in v)


def walk_points(o, fn, path=""):
    """apply fn(path, [x, y]) -> [x, y] to every geometric point outside NONPOINT/SKIP keys (EDGESTRIP-1 rule)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP_SUBTREES or k in NONPOINT:
                continue
            if is_pt(v):
                o[k] = fn(f"{path}/{k}", v)
            else:
                walk_points(v, fn, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if is_pt(v):
                o[i] = fn(f"{path}/{i}", v)
            else:
                walk_points(v, fn, f"{path}/{i}")


def walk_windows(o, fn, path="", face=None):
    """apply fn(path, face, [lo, hi]) to every *window_um of a face-carrying dict (buses, ft slots, ...)."""
    if isinstance(o, dict):
        f = o.get("face", face)
        for k, v in o.items():
            if k in WINKEYS and isinstance(v, list) and len(v) == 2 and all(isinstance(z, (int, float)) for z in v):
                fk = o.get({"in_window_um": "in_face", "out_window_um": "out_face"}.get(k, "face"), f)
                o[k] = fn(f"{path}/{k}", fk, v)
            elif isinstance(v, (dict, list)) and k not in ("verilog_defines", "count_straps"):
                walk_windows(v, fn, f"{path}/{k}", f)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk_windows(v, fn, f"{path}/{i}", face)


def cores(t):
    out = []
    for c in (t.get("hard_cores") or []) + [m for m in (t.get("contents") or []) if isinstance(m, dict)]:
        if "origin_um" in c and "outline_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            out.append((x, y, x + w, y + h, c.get("inst")))
    return out


def ns_windows(part, face):
    """die ports >= min-bits on the given die face of part -> type-frame x spans (R0/MY only)."""
    p = PL[PI[part]]
    W = T[p["type"]]["outline_um"][0]
    x0 = p["origin_um"][0]
    res = []
    opp = {"N": "S", "S": "N", "E": "W", "W": "E"}
    for pr in P["ports"]:
        if int(pr.get("width", 1) or 1) < a.min_bits or "window_um" not in pr or "face" not in pr:
            continue
        for side, f in (("src", pr["face"]), ("dst", opp[pr["face"]])):
            if pr[side]["part"] == part and f == face:
                lo, hi = sorted(pr["window_um"])
                s0, s1 = lo - x0, hi - x0
                if p.get("orient", "R0") == "MY":
                    s0, s1 = W - s1, W - s0
                res.append((s0, s1, pr["id"]))
    return res


def strip(t, face, wins):
    W, H = t["outline_um"]
    best = None
    for s0, s1, _ in wins:
        for x0, y0, x1, y1, _ in cores(t):
            if min(x1, s1) - max(x0, s0) <= 0.01:
                continue
            d = y0 if face == "S" else H - y1
            best = d if best is None else min(best, d)
    return best


def snap_out(q, B, W, H):
    """a moved point must not lie in a core/macro (plan_gate_pre GEOM refuses moved in-core sites even when the J8
    site was in-core and tolerated): push it to the nearest free spot just outside the box edge (EDGESTRIP-1 rule)."""
    x, y = q
    for _ in range(6):
        hit = [b for b in B if b[0] + 0.01 < x < b[2] - 0.01 and b[1] + 0.01 < y < b[3] - 0.01]
        if not hit:
            return [R(x), R(y)]
        b = hit[0]
        cands = [(x - b[0], b[0] - 0.54, y), (b[2] - x, b[2] + 0.54, y), (y - b[1], x, b[1] - 0.54), (b[3] - y, x, b[3] + 0.54)]
        cands = [c for c in cands if 0.3 < c[1] < W - 0.3 and 0.3 < c[2] < H - 0.3]
        free = [c for c in cands if not any(o[0] + 0.01 < c[1] < o[2] - 0.01 and o[1] + 0.01 < c[2] < o[3] - 0.01 for o in B)]
        c = min(free or cands)
        x, y = c[1], c[2]
    return [R(x), R(y)]


ops, rep = [], []
before = copy.deepcopy(P)
for lo in [s for s in a.lo.split(",") if s]:
    lx0, ly0, lx1, ly1 = box(lo)
    ups = sorted((n for n in PI if n != lo and abs(box(n)[1] - ly1) < 0.02 and min(box(n)[2], lx1) - max(box(n)[0], lx0) > 0.01),
                 key=lambda n: box(n)[0])
    r = {"lo": lo, "lo_type": PL[PI[lo]]["type"], "grown": [], "problems": []}
    pr_ = r["problems"]
    xs = [box(n)[0] for n in ups] + [box(ups[-1])[2]] if ups else []
    if not ups or abs(xs[0] - lx0) > 0.02 or abs(xs[-1] - lx1) > 0.02 or any(abs(box(ups[i])[2] - box(ups[i + 1])[0]) > 0.02 for i in range(len(ups) - 1)):
        pr_.append(f"abutters {ups} do not tile the N face of {lo} [{lx0}, {lx1}]")
    for n in ups:
        bx0, by0, bx1, by1 = box(n)
        under = [m for m in PI if m != n and abs(box(m)[3] - by0) < 0.02 and min(box(m)[2], bx1) - max(box(m)[0], bx0) > 0.01]
        if under != [lo]:
            pr_.append(f"{n} S face abuts {under}, not only {lo}")
    for n in [lo] + ups:
        p = PL[PI[n]]
        if NINST[p["type"]] != 1:
            pr_.append(f"type {p['type']} of {n} has {NINST[p['type']]} instances")
        if p.get("orient", "R0") not in ("R0", "MY"):
            pr_.append(f"{n} orient {p.get('orient')} (type N != die N)")
    if pr_:
        rep.append(r)
        problems += pr_
        continue
    # only where needed: some abutter has a >=MIN_BITS S window with a core < STRIP behind it
    need_s = {n: strip(T[PL[PI[n]]["type"]], "S", ns_windows(n, "S")) for n in ups}
    r["abutter_S_strip"] = {n: (None if v is None else R(v)) for n, v in need_s.items()}
    if all(v is None or v >= a.strip - 1e-6 for v in need_s.values()):
        r["status"] = "SKIP-NOT-NEEDED"
        rep.append(r)
        continue
    r["status"] = "APPLY"
    # --- LO: shrink at N
    ltn = PL[PI[lo]]["type"]
    lt = T[ltn]
    W, H = lt["outline_um"]
    Hn = R(H - G)
    lwins = ns_windows(lo, "N")
    need = a.strip if lwins else a.core_margin
    top = max(c[3] for c in cores(lt))
    if Hn - top < need - 1e-6:
        pr_.append(f"{ltn} N margin {R(H - top)} - {G} < {need}")
    mv_lo = []

    def lo_pt(path, v):
        """N-face points (on the N edge, or in the N strip >= G above the cores) move -G with the N face; E/W-face
        points keep their die y (their windows do); a point left in the removed band is refused."""
        ew = v[0] <= a.edge or v[0] >= W - a.edge
        if not ew and (v[1] >= H - a.edge or v[1] >= top + G - 1e-6):
            mv_lo.append(path)
            return snap_out([v[0], R(v[1] - G)], [c[:4] for c in cores(lt)], W, Hn)
        if v[1] > Hn - a.edge:
            pr_.append(f"{ltn}{path} {v} in the removed N band")
        return v

    lnew = copy.deepcopy(lt)
    lnew["outline_um"] = [W, Hn]
    walk_points({k: v for k, v in lnew.items() if k not in ("hard_cores", "contents")}, lo_pt)
    # 4-number rects (clock band / landing contract) and [[x],[y]] tap windows are shapes, not points: they move as one with the N face
    _lrest = {k: v for k, v in lnew.items() if k not in ("hard_cores", "contents", "outline_um")}
    r_shapes = RF.walk_shapes(_lrest, RF.n_edge_moves(H, top, G, a.edge), lambda m: pr_.append(f"{ltn}{m}"))
    lnew.update(_lrest)

    def lo_win(path, f, v):
        if f in ("E", "W") and max(v) > Hn + 1e-6:
            pr_.append(f"{ltn}{path} face {f} window {v} above new H {Hn}")
        return v

    walk_windows(lnew, lo_win)
    # die ports on LO's E/W faces must stay below the new top
    for prt in P["ports"]:
        if lo in (prt["src"]["part"], prt["dst"]["part"]) and prt.get("face") in ("E", "W") and "window_um" in prt:
            if max(prt["window_um"]) > ly1 - G + 1e-6:
                pr_.append(f"port {prt['id']} {prt['face']} window {prt['window_um']} above new {lo} top {R(ly1 - G)}")
    r["lo_H"] = [H, Hn]
    r["lo_N_moved_points"] = len(mv_lo)
    r["lo_N_moved_shapes"] = r_shapes
    r["lo_N_strip"] = [strip(lt, "N", lwins), strip(lnew, "N", lwins)]
    # --- abutters: grow at S
    gnew = {}
    for n in ups:
        tn = PL[PI[n]]["type"]
        t = T[tn]
        W2, H2 = t["outline_um"]
        new = copy.deepcopy(t)
        new["outline_um"] = [W2, R(H2 + G)]
        cnt = Counter()
        for c in (new.get("hard_cores") or []) + [m for m in (new.get("contents") or []) if isinstance(m, dict)]:
            if "origin_um" in c and "outline_um" in c:
                c["origin_um"] = [c["origin_um"][0], R(c["origin_um"][1] + G)]
                cnt["core"] += 1

        NB = [c[:4] for c in cores(new)]

        def gp(path, v):
            if v[1] <= a.edge:
                cnt["S-anchored"] += 1
                return v
            cnt["pt"] += 1
            q = [v[0], R(v[1] + G)]
            q2 = snap_out(q, NB, W2, H2 + G)
            if q2 != q:
                cnt["snapped-out"] += 1
            return q2

        rest = {k: v for k, v in new.items() if k not in ("hard_cores", "contents", "outline_um")}
        walk_points(rest, gp)
        cnt["shapes"] += RF.walk_shapes(rest, RF.s_grow_moves(G, a.edge), lambda m: pr_.append(f"{tn}{m}"))
        for k, v in rest.items():
            new[k] = v

        def gw(path, f, v):
            if f in ("E", "W"):
                cnt["EW-window"] += 1
                return [R(v[0] + G), R(v[1] + G)]
            if f is None:
                pr_.append(f"{tn}{path} window without face")
            return v

        walk_windows(new, gw)
        swins = ns_windows(n, "S")
        nwins = ns_windows(n, "N")
        st = {"S": [strip(t, "S", swins), strip(new, "S", swins)], "N": [strip(t, "N", nwins), strip(new, "N", nwins)]}
        for x0, y0, x1, y1, inst in cores(new):
            if y1 > H2 + G - a.core_margin + 0.01 or y0 < a.core_margin - 0.01:
                pr_.append(f"{tn} core {inst} past margin")
        gnew[n] = (tn, new)
        r["grown"].append({"part": n, "type": tn, "H": [H2, R(H2 + G)], "moved": dict(cnt), "strips": st})
    if pr_:
        rep.append(r)
        problems += pr_
        continue
    # --- commit
    T[ltn] = lnew
    for key in sorted(set(lnew) | set(lt)):
        if lnew.get(key) != lt.get(key):
            ops.append({"op": "replace", "path": f"/partition_types/{ltn}/{key}", "value": lnew[key]})
    ins = (P.get("reset") or {}).get("in_sites") or {}
    for n, (tn, new) in gnew.items():
        old = T[tn]
        T[tn] = new
        for key in sorted(set(new) | set(old)):
            if new.get(key) != old.get(key):
                ops.append({"op": "replace", "path": f"/partition_types/{tn}/{key}", "value": new[key]})
        i = PI[n]
        PL[i]["origin_um"] = [PL[i]["origin_um"][0], R(PL[i]["origin_um"][1] - G)]
        ops.append({"op": "replace", "path": f"/partitions/{i}/origin_um", "value": PL[i]["origin_um"]})
        if tn in ins and ins[tn][1] > a.edge:
            ins[tn] = [ins[tn][0], R(ins[tn][1] + G)]
            ops.append({"op": "replace", "path": f"/reset/in_sites/{tn}", "value": ins[tn]})
    if ltn in ins and ins[ltn][1] >= T[ltn]["outline_um"][1] + G - a.edge:
        ins[ltn] = [ins[ltn][0], R(ins[ltn][1] - G)]
        ops.append({"op": "replace", "path": f"/reset/in_sites/{ltn}", "value": ins[ltn]})
    rep.append(r)

# die-level overlap check on the result
bx = {n: box(n) for n in PI}
names = sorted(bx)
changed = {r["lo"] for r in rep if r.get("status") == "APPLY"} | {g["part"] for r in rep for g in r["grown"]}
for n in changed:
    b = bx[n]
    for m in names:
        if m == n:
            continue
        c = bx[m]
        if min(b[2], c[2]) - max(b[0], c[0]) > 0.01 and min(b[3], c[3]) - max(b[1], c[1]) > 0.01:
            problems.append(f"die overlap {n} {m}")
# any other die-level type-frame mention of a changed type
mention = Counter()
for k, v in P.items():
    if k in ("partition_types", "partitions", "ports"):
        continue
    s = json.dumps(v)
    for r in rep:
        if r.get("status") != "APPLY":
            continue
        for tn in [r["lo_type"]] + [g["type"] for g in r["grown"]]:
            if f'"{tn}"' in s:
                mention[(k, tn)] += 1
print(json.dumps(rep, indent=1))
print("die-level mentions of changed types (non-geometric unless listed above):", dict(mention))
print("problems", len(problems))
for p in problems[:40]:
    print(" ", p)
print("ops", len(ops))
if a.report:
    json.dump({"rows": rep, "problems": problems, "mentions": {f"{k}|{t}": c for (k, t), c in mention.items()}}, open(a.report, "w"), indent=1)
if problems:
    sys.exit(2)
if a.ops:
    json.dump({"schema": "opentallas.s81.die_row.v1", "row": "SVC-YTRADE-1", "lane": "OPUS-FIX-S81-SVC-R9",
               "params": vars(a), "ops": ops}, open(a.ops, "w"))
if a.apply:
    json.dump(P, open(a.apply, "w"))
    print("wrote", a.apply)
