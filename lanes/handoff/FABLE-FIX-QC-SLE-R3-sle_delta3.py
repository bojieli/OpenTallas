#!/usr/bin/env python3
"""FABLE-FIX-QC-SLE-R2 private plan delta for sle_ctl__cla4f6f12f (zero added cycles).
  sle_delta.py PLAN_IN PINS_PKL PLAN_OUT ROWS_OUT REPORT
1. hard cores: u_tap west 108 um, u_ctl east 38.88 um (moves only) -> 155.5-um tap/ctl channel, 52-um W strip.
2. every per-bit out station chain that crossed a core gets explicit per-bit FIRM sites (plan relay_sites, the kit's
   existing rs_place_all form) on a core-free polyline, stations at equal arclength per bit; nominal leaf_um/regs_um follow.
3. lane pads of x_fw_p2_i (tap.hr_q) per bit under u_ctl and up the channel; b_tw_data_i / x_st_b_i / x_hc*_i pad sites moved.
4. ft cws1 / cws2 station sites off the cores (cws2 east of u_ctl), >= 30 um off the core pin faces.
5. plan points that the moved cores now cover (collector relays, landing start stages, reset consumer sites) pushed out."""
import json, pickle, sys, re, copy, os
N_HC1 = int(os.environ.get("N_HC1", "0")); N_HC3 = int(os.environ.get("N_HC3", "0"))     # 0 = keep the plan's station count (V2: 7 / 8); V1 proof B used 5 / 4
pin_, pkl, pout, rout, rep_ = sys.argv[1:6]
TN = "sle_ctl__cla4f6f12f"; TAG = os.environ.get("SLE_TAG", "FABLE-FIX-QC-SLE-R3 11-21")
P = json.load(open(pin_)); t = P["partition_types"][TN]
_t0, PINS = pickle.load(open(pkl, "rb"))
PD = pin_.rsplit("/", 1)[0] + "/"
DT = (-108.0, 0.0); DC = (38.88, 0.0)
hc = {c["inst"]: c for c in t["hard_cores"]}
old = {k: tuple(hc[k]["origin_um"]) for k in ("u_tap", "u_ctl")}
def cpins(inst, plan_dir):
    c = hc[inst]; pj = json.load(open(plan_dir + c["pins_file"]))
    return {p["name"]: (c["origin_um"][0] + float(p["x"]), c["origin_um"][1] + float(p["y"])) for p in pj["pins"]}
PLAN_DIR = sys.argv[6] if len(sys.argv) > 6 else PD
for k, d in (("u_tap", DT), ("u_ctl", DC)):
    hc[k]["origin_um"] = [round(old[k][0] + d[0], 4), round(old[k][1] + d[1], 4)]
    hc[k]["note"] = (hc[k].get("note", "") + f" | {TAG}: moved {d[0]:+g},{d[1]:+g} um (no reshape): opens the tap/ctl slit").strip(" |")
TP = cpins("u_tap", PLAN_DIR); CP = cpins("u_ctl", PLAN_DIR)
BOX = {k: (hc[k]["origin_um"][0], hc[k]["origin_um"][1], hc[k]["origin_um"][0] + hc[k]["outline_um"][0],
           hc[k]["origin_um"][1] + hc[k]["outline_um"][1]) for k in hc}
TB, CB = BOX["u_tap"], BOX["u_ctl"]
for tp in t["clock"]["taps"]:
    for k, d in (("u_tap", DT), ("u_ctl", DC)):
        if tp["name"] == k + ".ck":
            tp["xy"] = [round(tp["xy"][0] + d[0], 4), round(tp["xy"][1] + d[1], 4)]
md = lambda a, c: abs(a[0] - c[0]) + abs(a[1] - c[1])
def plen(pts): return sum(md(a, c) for a, c in zip(pts, pts[1:]))
def at(pts, s):
    for a, c in zip(pts, pts[1:]):
        d = md(a, c)
        if s <= d + 1e-9:
            f = s / d if d else 0.0
            return (a[0] + f * (c[0] - a[0]), a[1] + f * (c[1] - a[1]))
        s -= d
    return pts[-1]
def seg_hits(a, c, box, tol=0.5):
    x0, x1, y0, y1 = min(a[0], c[0]), max(a[0], c[0]), min(a[1], c[1]), max(a[1], c[1])
    return x0 < box[2] - tol and x1 > box[0] + tol and y0 < box[3] - tol and y1 > box[1] + tol
def inbox(p, box, h=0.0): return box[0] - h < p[0] < box[2] + h and box[1] - h < p[1] < box[3] + h
buses = {b["name"]: b for b in t["buses"]}
ist = {e["conn"][4:]: e for e in t["internal_stations"] if e["conn"].startswith("bus:")}
N0 = {k: len(e["regs_um"]) for k, e in ist.items()}
rs = t["relay_sites"]; REP = {"rows": {}, "moved_points": [], "note": TAG}
def hw_x(j): return TP[f"hw[{j}]"][0]
YS = 318.0                                   # exit row 10 um under the tap S pin row
FACES = [(TB[0] + 20, TB[1] - 30, TB[2] - 20, TB[1]), (TB[2], TB[1] + 8, TB[2] + 30, TB[3] - 8), (TB[0] + 140, TB[3], TB[0] + 165, TB[3] + 30),
         (CB[0] - 30, CB[1] + 15, CB[0], CB[3] - 15), (CB[0] + 20, CB[1] - 30, CB[2] - 20, CB[1]), (CB[2], CB[1] + 25, CB[2] + 30, CB[3] - 25),
         (CB[0] + 5, CB[3], CB[2] - 5, CB[3] + 30)]          # 30-um keep-off strips in front of the tap / ctl pin rows
def slide(pts, L, s0):
    """core-slide: a site inside a hard-core box (+3 um) or a 30-um pin-row keep-off strip moves along its own route to the nearest free point"""
    for d in range(0, 400):
        for sg in (1, -1):
            s = s0 + sg * d * 2.0
            if 0 <= s <= L:
                q = at(pts, s)
                if not any(inbox(q, bx, 3.0) for bx in BOX.values()) and not any(inbox(q, fb) for fb in FACES): return q, d * 2.0
    raise SystemExit("no free point on route")
XM = {}
def chain(bus, pathf, note, n=None):
    e = ist[bus]; pp = PINS[bus]; W = max(pp); n0 = len(e["regs_um"]); n = n or n0
    sums = [[0.0, 0.0] for _ in range(n)]; worst = 0.0; cross = 0; incore = 0; nearface = 0; first = 0.0; slid = 0; hopmax = 0.0
    for b in range(W + 1):
        px, py, _f = pp[b]; f = (b + 0.5) / (W + 1)
        pts, src = pathf(b, f, px, py, W)
        L = plen(pts); worst = max(worst, L / (n + 1))
        for a, c in zip(pts, pts[1:]):
            hb = [nm for nm, bx in BOX.items() if seg_hits(a, c, bx)]
            if hb: cross += 1; XM.setdefault(bus, {}).setdefault(hb[0], 0); XM[bus][hb[0]] += 1; break
        prev = src if src is not None else pts[0]
        for k in range(n):
            s, dd = slide(pts, L, L * (k + 1) / (n + 1))
            slid += dd > 0
            if any(inbox(s, bx, 2.0) for bx in BOX.values()): incore += 1
            if any(inbox(s, fb) for fb in FACES): nearface += 1
            hopmax = max(hopmax, md(prev, s)); prev = s
            key = f"u_ist_{bus}_{k}." + (f"q[{b}]" if b < W else "eq")
            rs[key] = [round(s[0], 3), round(s[1], 3)]; sums[k][0] += s[0]; sums[k][1] += s[1]
            if k == 0 and src is not None: first = max(first, md(src, s))
    e["regs_um"] = [[round(x / (W + 1), 3), round(y / (W + 1), 3)] for x, y in sums]
    e["note"] = (e.get("note", "") + f" | {TAG}: {note}; per-bit FIRM sites in relay_sites (u_ist_{bus}_<k>.q[b]), equal arclength per bit, "
                 f"worst planned hop {worst:.1f} um, 0 cycles").strip(" |")
    REP["rows"][bus] = dict(stations=n, stations_before=n0, bits=W + 1, worst_hop_um=round(worst, 1), first_hop_from_source_um=round(first, 1),
                            worst_site_to_site_um=round(hopmax, 1), routes_crossing_hard_macros=cross, sites_in_core=incore,
                            sites_slid_out_of_a_macro=slid, sites_within_30um_of_tap_ctl_pin_rows=nearface)
def src_hw(b, W, lo=6):
    if lo <= b < lo + 1567: p = TP[f"hw[{b - lo}]"]; return (p[0], YS), p
    return ((hw_x(0) if b < lo else hw_x(1566)), YS), None
def p_hc0(b, f, px, py, W):
    s, src = src_hw(b, W); return [s, (s[0], py), (px, py)], src
def p_hc3(b, f, px, py, W):
    s, src = src_hw(b, W); yg = 100.0 + 190.0 * f
    if py > 295.0:      # E pins up to y 333 sit level with the u_ctl S pin row (337): run east 40-65 um under it, rise east of u_ctl
        ye = 295.0 - (py - 295.0) * 0.65
        return [s, (s[0], yg), (400.0, yg), (400.0, ye), (900.0, ye), (900.0, py), (px, py)], src
    return [s, (s[0], yg), (400.0, yg), (400.0, py), (px, py)], src
def p_hc1(b, f, px, py, W):
    s, src = src_hw(b, W); xg = 390.0 + 94.0 * f; yg = 490.0 + 70.0 * f
    if px < 78.0:       # W-face landing macros cl_x_st_a_i / cl_x_fw_i / cl_x_st_a_st_b_i (x 17-76, y 570-830): pass east of them
        g = px / 78.0; xv = 80.0 + 40.0 * g; yj = 838.0 + 40.0 * g
        return [s, (xg, YS), (xg, yg), (xv, yg), (xv, yj), (px, yj), (px, py)], src
    return [s, (xg, YS), (xg, yg), (px, yg), (px, py)], src
def p_hc2(b, f, px, py, W):
    s, src = src_hw(b, W); yh = 296.0 - 56.0 * f; xg = 390.0 + 94.0 * f; yg = 628.0 + 90.0 * f
    return [s, (s[0], yh), (xg, yh), (xg, yg), (px, yg), (px, py)], src
def p_sta(b, f, px, py, W):
    x0 = 400.0 - 70.0 * f; y0 = 296.0 - 84.0 * f; xg = 10.0 + 38.0 * f
    src = CP[f"stn_cfg[{b}]"] if b < 29 else None
    return [(x0, y0), (xg, y0), (xg, py), (px, py)], src
def p_fwo(b, f, px, py, W):
    nm = f"ag_own[{b}]" if b < 10 else f"cc_o[{b - 10}]" if b < 60 else f"own_ch[{b - 60}]"
    src = CP.get(nm) if b < W else None
    yc = src[1] if src else CP["own_ch[570]"][1]
    xs = CB[0] - 30.0; xg = 470.0 - 70.0 * f; yr = max(py, 490.0)
    if yr > py + 1e-6: return [(xs, yc), (xg, yc), (xg, yr), (30.0, yr), (30.0, py), (px, py)], src
    return [(xs, yc), (xg, yc), (xg, py), (px, py)], src
def p_stb(b, f, px, py, W):
    src = CP[f"stn_cfg[{b}]"] if b < W else None
    return [(CB[0] - 24.0, 358.0), (CB[0] - 24.0, 300.0), (1100.0, 300.0), (1100.0, py), (px, py)], src
def p_p1(b, f, px, py, W):
    xg = 895.0 + 65.0 * f
    return [(900.0, 600.0), (xg, 600.0), (xg, 300.0), (px, 300.0), (px, py)], None
chain("b_hw_hc0_o", p_hc0, "launch row under the tap S pins, straight to the W pins")
chain("b_hw_hc3_o", p_hc3, "launch row under the tap S pins, east under u_ctl clear of cl_b_tw_data_i" + (f"; {N0['b_hw_hc3_o']} -> {N_HC3} stations" if N_HC3 else ""), N_HC3 or None)
chain("b_hw_hc1_o", p_hc1, "two-knee route: under the tap, up the tap/ctl channel, over the tap N edge" + (f"; {N0['b_hw_hc1_o']} -> {N_HC1} stations" if N_HC1 else ""), N_HC1 or None)
chain("b_hw_hc2_o", p_hc2, "two-knee route: under the tap, up the tap/ctl channel, over the u_ctl N edge")
chain("b_tw_data_st_a_o", p_sta, "west under the tap, up the W strip per bit")
chain("x_fw_o", p_fwo, "30 um off the u_ctl W pin face, up the channel, west over the tap N edge")
chain("x_st_b_o", p_stb, "around the u_ctl SW corner, east under u_ctl")
chain("x_su_c_p1_o", p_p1, "east of u_ctl (35 um off the E pin face)")
for bus, leaf in (("b_hw_hc0_o", [156.0, 318.0]), ("b_hw_hc3_o", [156.0, 318.0]), ("b_hw_hc1_o", [300.0, 318.0]), ("b_hw_hc2_o", [480.0, 318.0]),
                  ("b_tw_data_st_a_o", [300.0, 262.0]), ("x_fw_o", [round(CB[0] - 30.0, 3), 438.0]), ("x_su_c_p1_o", [900.0, 593.42]),
                  ("x_su_c_p2_o", [905.0, 330.0])):
    e = ist[bus]; e["leaf_um"] = leaf; e["from_um"] = leaf
e = ist["x_su_c_p2_o"]; _p = [(905.0, 330.0), (998.0, 330.0), (998.0, 0.0)]; _n = len(e["regs_um"])
e["regs_um"] = [[998.0, 330.0]] if _n == 1 else [[round(v, 3) for v in at(_p, plen(_p) * (k + 1) / (_n + 1))] for k in range(_n)]
e["note"] = (e.get("note", "") + f" | {TAG}: leaf east of the moved u_ctl SE corner").strip(" |")
# x_fw_p2_i lane pad (D2): hr_q bits 82..534 per bit under u_ctl and up the channel; rp bits stay NE of u_ctl
e = ist["x_fw_p2_i"]; W = 536; assert len(e["regs_um"]) == 2, "x_fw_p2_i lane pad is no longer D2: re-derive the per-bit pad sites"
worst = 0.0; N = 453; sm = [[0.0, 0.0], [0.0, 0.0]]; XBIN = 960.0
for k in list(rs):          # face register sites of x_fw_p2_i: 1022 -> 960 (62 um nearer the tap, 100 um off the u_ctl E face)
    if k.startswith("u_bin_x_fw_p2_i/"): rs[k] = [XBIN, rs[k][1]]
for b in range(W + 1):
    if 82 <= b <= 534:
        i = b - 82; g = (i + 0.5) / N
        yb = rs.get(f"u_bin_x_fw_p2_i/q[{b}]", [1022.0, 390.0])[1]; yp = TP[f"hr_q[{i}]"][1]
        yh = 275.0 + 30.0 * g; xc = 388.0 + 82.0 * g
        pts = [(XBIN, yb), (XBIN, yh), (xc, yh), (xc, yp), (TB[2], yp)]; L = plen(pts); worst = max(worst, L / 3)
        s = [at(pts, L / 3), at(pts, 2 * L / 3)]
        assert not any(seg_hits(a, c, bx) for a, c in zip(pts, pts[1:]) for bx in BOX.values())
    else:
        s = [(1000.0, 470.0), (960.0, 500.0)]
    rs[f"u_lpad_x_fw_p2_i.r[0][{b}]"] = [round(s[0][0], 3), round(s[0][1], 3)]
    rs[f"u_lpad_x_fw_p2_i.q[{b}]"] = [round(s[1][0], 3), round(s[1][1], 3)]
    for k in (0, 1): sm[k][0] += s[k][0]; sm[k][1] += s[k][1]
e["regs_um"] = [[round(x / (W + 1), 3), round(y / (W + 1), 3)] for x, y in sm]; e["leaf_um"] = [round(TB[2] + 30.0, 3), 394.0]; e["to_um"] = e["leaf_um"]
e["note"] = (e.get("note", "") + f" | {TAG}: lane pad stages per bit (relay_sites u_lpad_x_fw_p2_i.r[0][b] / .q[b]): tap.hr_q bits under u_ctl and up "
             f"the channel (worst hop {worst:.1f} um), u_rp bits NE of u_ctl; 0 cycles").strip(" |")
REP["rows"]["x_fw_p2_i"] = dict(stations=2, worst_hop_um=round(worst, 1))
def setregs(bus, regs, note, leaf=None):
    e = ist[bus]; assert len(e["regs_um"]) == len(regs), bus
    e["regs_um"] = [[round(x, 3), round(y, 3)] for x, y in regs]
    if leaf: e["leaf_um"] = leaf; e["to_um"] = leaf
    e["note"] = (e.get("note", "") + f" | {TAG}: {note}").strip(" |"); REP["rows"][bus] = dict(regs_um=e["regs_um"])
def spread(bus, pts): n = N0[bus]; L = plen(pts); return [at(pts, L * (k + 1) / (n + 1)) for k in range(n)]
setregs("b_tw_data_i", [(281.956, 112.324), (284.0, 232.0)] if N0["b_tw_data_i"] == 2 else spread("b_tw_data_i", [(281.956, 66.0), (284.0, 66.0), (284.0, 300.0)]), "second pad stage under the moved tap xt pins", [284.0, 318.0])
setregs("x_st_b_i", [(1010.0, 500.0), (950.0, 515.0), (900.0, 530.0)] if N0["x_st_b_i"] == 3 else spread("x_st_b_i", [(1150.0, 560.0), (1150.0, 500.0), (1010.0, 500.0), (1010.0, 530.0), (CB[2] + 30.0, 530.0)]), "pad stages lead to the u_ctl E pin face (r_d), 40 um off it", [round(CB[2] + 30.0, 3), 532.0])
TN_ = (TP["lq_bad[16]"][0], TB[3] + 30.0)        # 30 um over the tap N pin face
for bus in ("x_hc0_i", "x_hc1_i", "x_hc2_i", "x_hc3_i"):
    e = ist[bus]; n = len(e["regs_um"]); a = tuple(e["from_um"]); ym = max(640.0, TN_[1])
    far = a[0] > CB[0] - 40
    pts = [a, (a[0], ym), (TN_[0], ym)] if far else [a, (a[0], TN_[1]), TN_]
    L = plen(pts); setregs(bus, [at(pts, L * (k + 1) / (n + 1)) for k in range(n)], "pad stages lead to the tap N pin face (lq_bad) over u_ctl",
                           [round(TN_[0], 3), ym if far else round(TN_[1], 3)])
e = ist["x_su_l0_i"]; e["leaf_um"] = [round(CB[2] + 30.0, 3), e["leaf_um"][1]]; e["to_um"] = e["leaf_um"]
# the 444 FIRM last-stage sites of u_lpad_x_su_l0_i sat 45 um east of the old u_ctl E edge: keep that offset
nmv = 0
for k in list(rs):
    if k.startswith("u_lpad_x_su_l0_i.q["): rs[k] = [round(rs[k][0] + DC[0], 3), rs[k][1]]; nmv += 1
REP["u_lpad_x_su_l0_i_sites_shifted"] = nmv
# ft slots (landed: station i sits at regs_um[i + 1], the last one at the out face)
for s in t["ft_slots"]:
    # re-derived from the landing macro position of THIS plan (V2 moved cl_cws1_i / cl_cws2_i +116.64 um in y): equal arclength from the
    # macro S edge to the out window; station i at regs_um[i + 1], the last one at the out face
    if s["name"] in ("cws1", "cws2"):
        mb = BOX["cl_" + s["name"] + "_i"]; n = int(s["stations"]); ox = sum(s["out_window_um"]) / 2.0; x0 = min(max(s["regs_um"][0][0], mb[0]), mb[2])
        if s["name"] == "cws1": pts = [(x0, mb[1]), (436.0, mb[1]), (436.0, 30.0), (ox, 30.0), (ox, 0.0)]
        else: pts = [(x0, mb[1]), (942.0, mb[1]), (942.0, 296.0), (ox, 296.0), (ox, 0.0)]
        assert not any(seg_hits(a, c, bx) for a, c in zip(pts, pts[1:]) for nm, bx in BOX.items() if nm in ("u_tap", "u_ctl")), s["name"]
        L = plen(pts); q = [at(pts, L * k / n) for k in range(1, n)]
        if os.environ.get("CWS_R2") == "1":        # the exact R2 sites (V1 proof k_a / k_b)
            q = {"cws1": [[436.0, 955.5], [436.0, 629.0], [436.0, 302.5]], "cws2": [[940.0, 876.0], [945.0, 586.0], [941.0, 300.0], [662.0, 289.0]]}[s["name"]]
        assert len(s["regs_um"]) == n, (s["name"], len(s["regs_um"]), n)
        s["regs_um"] = [s["regs_um"][0]] + [[round(v[0], 3), round(v[1], 3)] for v in q]
        for kk in ("bit_sites_um",):
            if kk in s: REP.setdefault("ft_bit_sites_dropped", []).append(s["name"]); del s[kk]
        REP.setdefault("ft_hop_um", {})[s["name"]] = round(L / n, 1)
REP["ft"] = {s["name"]: s["regs_um"] for s in t["ft_slots"] if s.get("regs_um")}
# plan points now under a moved core: out to the nearest box edge + 6 um (start stages that hugged the old tap W edge move with it)
def push(p):
    for bx in (TB, CB):
        if inbox(p, bx, 2.0):
            c = [(p[0] - bx[0], (bx[0] - 6.0, p[1])), (bx[2] - p[0], (bx[2] + 6.0, p[1])), (p[1] - bx[1], (p[0], bx[1] - 6.0)), (bx[3] - p[1], (p[0], bx[3] + 6.0))]
            q = min(c)[1]; return [round(q[0], 3), round(q[1], 3)]
    return None
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("xy", "xy_um") and isinstance(v, list) and len(v) == 2 and not str(o.get("name", "")).endswith(".ck"):
                q = push(v)
                if q: REP["moved_points"].append([path + "/" + k, v, q]); o[k] = q
            else: walk(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, list) and len(v) == 3 and isinstance(v[0], str) and all(isinstance(z, (int, float)) for z in v[1:]):
                q = push(v[1:])
                if q: REP["moved_points"].append([path + "/" + v[0], v[1:], q]); o[i] = [v[0]] + q
            else: walk(v, path + f"[{i}]")
walk(t["clock"], "clock"); walk(t["reset"], "reset")
# residual census: every station / pad / ft / relay site against every hard-core box
left = [k for k, v in rs.items() if any(inbox(v, bx, 0.5) for bx in BOX.values())]
REP["relay_sites_in_core"] = len(left); REP["relay_sites_in_core_e.g."] = left[:6]
REP["regs_in_core"] = [e["conn"] for e in t["internal_stations"] for r in e["regs_um"] if any(inbox(r, bx, 0.5) for bx in BOX.values())]
REP["ft_regs_in_core"] = [s["name"] for s in t["ft_slots"] for r in (s.get("regs_um") or []) if any(inbox(r, bx, 0.5) for bx in BOX.values())]
REP["routes_over_macros_M6_M8"] = XM
REP["added_cycles"] = {"b_hw_hc1_o": (N_HC1 - N0["b_hw_hc1_o"]) if N_HC1 else 0, "b_hw_hc3_o": (N_HC3 - N0["b_hw_hc3_o"]) if N_HC3 else 0}
# lanes: +delta fixed_cycles on every lane launched from the bus on a partition of this type, latency.lanes rows in step
# (the QC-PLAN-R6 r6_bus_stations.py / r6_lat_sync.py accounting)
ptype = {x["name"]: x["type"] for x in P["partitions"]}
ports = P["ports"] if isinstance(P["ports"], dict) else {x["id"]: x for x in P["ports"]}
lanes = []
for l in P["lanes"]:
    a = ports[l["ports"][0]].get("src")
    d = REP["added_cycles"].get((a or {}).get("bus"), 0)
    if a and d and ptype.get(a.get("part")) == TN:
        l["fixed_cycles"] = int(l.get("fixed_cycles", 0)) + d
        r = P["latency"]["lanes"][l["id"]]
        for k in ("fixed", "cycles", "natural"): r[k] = int(r[k]) + d
        lanes.append([l["id"], d, r["cycles"]])
REP["lanes_raised"] = lanes
REP["boxes"] = {"u_tap": TB, "u_ctl": CB}; REP["relay_sites_total"] = len(rs)
t["note"] = (t.get("note", "") + f" | {TAG}: tap/ctl channel 155.5 um, per-bit station sites off the cores (lanes/handoff/FABLE-FIX-QC-SLE-R2.md)").strip(" |")
json.dump(P, open(pout, "w"), separators=(",", ":")); json.dump({"partition_types": {TN: t}, "lanes_raised": lanes, "note": TAG + ": apply = replace the type + fixed_cycles/latency.lanes +d on lanes_raised"}, open(rout, "w"), separators=(",", ":"))
json.dump(REP, open(rep_, "w"), indent=1)
print(json.dumps({k: v for k, v in REP.items() if k != "moved_points"}, indent=1)[:6000]); print("moved points", len(REP["moved_points"]))
