#!/usr/bin/env python3
"""KV-HGSPLIT-1115: rebind landing rings >= 250 bits of the KV hg/hgi types as hard ring child cores (OVERSIZE-1 form).

usage: hgsplit.py BASE_PLAN OUT_PLAN_DIR [--types t1,t2] [--no-reset-net] [--rk RKDIR] [--margin 17.28]
Writes OUT_PLAN_DIR/plan_c.json (+ cores/kv_ring/<master>_pins.json, hgsplit_rows.tsv).  Run with python3 -I from the
tree root (tools/die_plan on the path).  Geometry: macro placed in free type area nearest its old band, with the
master's d face on the bus face (ew master: W R0 / E MY; ns master: S R0 / N MX).
"""
import argparse, glob, json, math, os, re, sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import check as CK
import schema as SCH

ap = argparse.ArgumentParser()
ap.add_argument("base"); ap.add_argument("outdir")
ap.add_argument("--types", default="")
ap.add_argument("--no-reset-net", action="store_true")
ap.add_argument("--rk", default="/srv/opentallas-scratch2/claude/cland-macro-1/rk")
ap.add_argument("--margin", type=float, default=17.28)
ap.add_argument("--min-w", type=int, default=250)
ap.add_argument("--grid", type=float, default=8.64)
ap.add_argument("--keep-taps", action="store_true")
ap.add_argument("--move-sites", action="store_true")
ap.add_argument("--ban-um", type=float, default=20.0)
ap.add_argument("--site-clear", type=float, default=2.0)
ap.add_argument("--toff", default="0.012,0.012")
a = ap.parse_args()
TOFF = [float(x) for x in a.toff.split(",")]
plan = json.load(open(a.base))
pt = plan["partition_types"]
out = Path(a.outdir)
PLAN_OBJ = SCH.Plan(plan, out / 'die_plan.json')
(out / "cores/kv_ring").mkdir(parents=True, exist_ok=True)

# ---- masters ----
masters, byk = {}, {}
for d in sorted(glob.glob(a.rk + "/kv_cland_*")):
    m = os.path.basename(d)
    try:
        c = json.load(open(d + "/config.json")); p = json.load(open(d + "/pins.json"))
    except OSError:
        continue
    cells = None
    for f in glob.glob(d + "/kits/*/native_cell_count.json"):
        try:
            cells = json.load(open(f))["stdcells"]
        except Exception:
            pass
    masters[m] = dict(cfg=c, pins=p, cells=cells)
    byk[(json.dumps(c["params"], sort_keys=True), c["orient"])] = m


def face_of(t, bus):
    o = pt[t]["outline_um"]
    for p in pt[t]["clock"]["landing_contract"]["pins"]:
        if p["name"] == "fclk_in_" + bus:
            x, y = p["xy_um"]
            d = {"W": x, "E": o[0] - x, "S": y, "N": o[1] - y}
            return min(d, key=d.get)


def predict(t, w):
    ty = pt[t]; W = w + 1
    pr = dict(W=W, DEPTH=4)
    if ty.get("landing_control_status_copy"):
        pr["CONTROL_STATUS_COPY"] = 1
    pr.update(STATUS_REG=1, GUARD_REG=1, WFALL=1, WREG=1, DSREP=8, RSTREP=2 * (-(-W // 64)) + 1)
    return pr


ORI = {("ew", "W"): "R0", ("ew", "E"): "MY", ("ns", "S"): "R0", ("ns", "N"): "MX"}
G = a.grid


def snap(v, up):
    return (math.ceil(v / G - 1e-9) if up else math.floor(v / G + 1e-9)) * G


def free(rect, obs):
    x0, y0, x1, y1 = rect
    return not any(x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1] for b in obs)


def pt_in(rect, pts, m):
    x0, y0, x1, y1 = rect
    return any(x0 - m < x < x1 + m and y0 - m < y < y1 + m for x, y in pts)


BIN = 20.0
_bins = {}


def bin_sites(pts):
    _bins.clear()
    for x, y, m in pts:
        _bins.setdefault((int(x // BIN), int(y // BIN)), []).append((x, y, m))


def pt_in3(rect, pts):
    x0, y0, x1, y1 = rect
    for bx in range(int((x0 - 9) // BIN), int((x1 + 9) // BIN) + 1):
        for by in range(int((y0 - 9) // BIN), int((y1 + 9) // BIN) + 1):
            for x, y, m in _bins.get((bx, by), ()):
                if x0 - m < x < x1 + m and y0 - m < y < y1 + m:
                    return True
    return False


import reset_tree as RT


def tapsig(tn):
    RT._TAPS.pop((id(PLAN_OBJ), tn), None)
    return [(n, round(x, 4), round(y, 4)) for n, x, y in RT._plan_taps(PLAN_OBJ, tn)]


base_sig = {}
rows = []
targets = a.types.split(",") if a.types else [t for t in pt if t.startswith("kv3_hg")]
for tn in targets:
    t = pt[tn]; W_, H_ = t["outline_um"]
    lc = t["clock"]["landing_contract"]; bands = lc["bands"]
    big = [(b, v) for b, v in bands.items() if v["width"] >= a.min_w and not v.get("hard_core")]
    if not big:
        continue
    obs = []
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; hl = h.get("halo_um") or 4.32
        obs.append((x - hl, y - hl, x + w + hl, y + hh + hl))
    big_names = {b for b, _ in big}
    for b, v in bands.items():
        if b not in big_names:
            obs.append(tuple(v["rect_um"]))
    pts = []
    for f in t.get("ft_slots", []):
        pts += [tuple(r) for r in (f.get("regs_um") or [])]
    for f in t.get("internal_stations", []) or []:
        pts += [tuple(r) for r in (f.get("regs_um") or [])]
    for tp in t["clock"]["taps"]:
        if tp.get("xy"):
            pts.append(tuple(tp["xy"]))
    for pinr in lc["pins"]:
        pts.append(tuple(pinr["xy_um"]))
    # die clock taps (R4 grid + clock.added_taps) keep TAP_CLEAR_UM off every macro (taps.grid_explicit_sites)
    tapclr = SCH.TAP_CLEAR_UM + 0.01
    taps_xy = [(x, y) for _, x, y in SCH._grid_taps(PLAN_OBJ, tn)] + [tuple(map(float, q["xy"])) for q in (t["clock"].get("added_taps") or [])]
    # every other planned site of the type (reset local taps, relay / reader-start / collector sites, stations, pins):
    # 4.32 um (reset_tree.CLEAR_UM) clear of every macro; the old band's own collector point moves with the ring
    sites = []
    KEYS = ("xy", "xy_um", "pin_xy_um", "local_taps_um", "regs_um", "root", "outs", "start_in", "sites_um", "status_pins_xy_um", "bit_sites_um")
    SKIP = ("hard_cores", "buses", "contents", "census", "count_straps", "sink_sites_um", "reach_fix_sinks")

    def walk(o, key, skipnames, rst):
        if isinstance(o, dict):
            if o.get("name") in skipnames and "band" in o:
                return
            for k, v in o.items():
                if k in SKIP:
                    continue
                if a.move_sites and k in ("landing_reader_start", "landing_writer_start", "landing_raw_branches", "added_taps", "collector_tree"):
                    continue
                walk(v, k, skipnames, rst or k in ("reset", "collector_tree", "collector_children", "collector_root_node"))
        elif isinstance(o, list):
            if len(o) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in o):
                if key in KEYS:
                    sites.append((float(o[0]), float(o[1]), 4.33 if (rst or key in ("local_taps_um", "root", "outs", "start_in")) else (1.0 if key == "bit_sites_um" else a.site_clear)))
            else:
                for v in o:
                    walk(v, key, skipnames, rst)
    walk({k: v for k, v in t.items() if k not in SKIP}, "", big_names, False)
    bin_sites(sites)
    base_sig[tn] = tapsig(tn)
    mg = a.margin
    for b, v in sorted(big, key=lambda bv: -bv[1]["width"]):
        f = face_of(tn, b)
        pr = predict(tn, v["width"])
        pin = next(q["xy_um"] for q in lc["pins"] if q["name"] == "fclk_in_" + b)
        r0 = v["rect_um"]
        cx, cy = (r0[0] + r0[2]) / 2, (r0[1] + r0[3]) / 2
        banned = set()
        while True:
            best = None
            for ax in (("ew", "ns") if f in "WE" else ("ns", "ew")):
                mk0 = byk.get((json.dumps(pr, sort_keys=True), ax))
                if mk0 is None:
                    continue
                cw, ch = masters[mk0]["pins"]["outline_um"]
                for ori, dface in ((("R0", "W"), ("MY", "E")) if ax == "ew" else (("R0", "S"), ("MX", "N"))):
                    for i in range(-int(W_ / G) - 1, int(W_ / G) + 2):
                        for j in range(-int(H_ / G) - 1, int(H_ / G) + 2):
                            ox = i * G; oy = j * G
                            rect = (ox, oy, ox + cw, oy + ch)
                            if rect[0] < mg - 1e-6 or rect[1] < mg - 1e-6 or rect[2] > W_ - mg + 1e-6 or rect[3] > H_ - mg + 1e-6:
                                continue
                            fx, fy = {"W": (ox, oy + ch / 2), "E": (ox + cw, oy + ch / 2), "S": (ox + cw / 2, oy), "N": (ox + cw / 2, oy + ch)}[dface]
                            dist = abs(ox + cw / 2 - cx) + abs(oy + ch / 2 - cy) + 0.5 * (abs(fx - pin[0]) + abs(fy - pin[1]))
                            if best is not None and dist >= best[0]:
                                continue
                            if any(rect[0] < bx1 and rect[2] > bx0 and rect[1] < by1 and rect[3] > by0 for bx0, by0, bx1, by1 in banned):
                                continue
                            if not free(rect, obs) or pt_in(rect, pts, 1.2) or pt_in(rect, taps_xy, tapclr) or pt_in3(rect, sites):
                                continue
                            best = (dist, ox, oy, mk0, ori, ax, dface)
            if best is None:
                break
            if not a.keep_taps:
                break
            # die clock taps and the reset / landing numbering hang on the tap table (grid legalizer + density taps move
            # when a box edge appears): accept a site only if the type's tap table is unchanged
            mkt, orit = best[3], best[4]; cwt, cht = masters[mkt]["pins"]["outline_um"]
            stub = dict(inst="cl_" + b, module=mkt, origin_um=[round(best[1], 3), round(best[2], 3)], outline_um=[cwt, cht],
                        orient=orit, track_offset_um=TOFF)
            PLAN_OBJ.types[tn]["hard_cores"].append(stub)
            if tapsig(tn) == base_sig[tn]:
                if PLAN_OBJ.types[tn]["hard_cores"] is t["hard_cores"]:
                    PLAN_OBJ.types[tn]["hard_cores"].pop()      # shared list: the real row is appended below
                break
            PLAN_OBJ.types[tn]["hard_cores"].pop()
            banned.add((best[1] - a.ban_um, best[2] - a.ban_um, best[1] + cwt + a.ban_um, best[2] + cht + a.ban_um))
        print("ring", tn, b, "NO_SITE" if best is None else "ok", "banned", len(banned), flush=True)
        if best is None:
            rows.append(dict(type=tn, bus=b, W=v["width"] + 1, status="NO_SITE", face=f))
            continue
        mk, ori, ax = best[3], best[4], best[5]
        M = masters[mk]; cw, ch = M["pins"]["outline_um"]
        _, ox, oy = best[:3]
        ox, oy = round(ox, 3), round(oy, 3)
        obs.append((ox - 2.16, oy - 2.16, ox + cw + 2.16, oy + ch + 2.16))
        inst = "cl_" + b
        pf = f"cores/kv_ring/{mk}_pins.json"
        (out / pf).write_text(json.dumps(M["pins"], indent=1) + "\n")
        hc = dict(inst=inst, module=mk, origin_um=[ox, oy], outline_um=[cw, ch], orient=ori,
                  track_offset_um=TOFF, pins_file=pf, physical_inst="u_bound.u_cland_" + b, physical_master=mk,
                  param_wrap=dict(base="ot_dp_clk_landing_cas", params=json.loads(json.dumps(pr))),
                  cells=(M["cells"] or int(24.9 * (v["width"] + 1))),
                  cells_basis=("CLAND-MACRO-1 master native_cell_count stdcells" if M["cells"] else "24.9 cells/bit (measured on kv_cland_w1057_ew_94a44: 26293/1057)"),
                  note="KV-HGSPLIT-1115 (OVERSIZE-1 form): landing ring u_cland_%s as a hard child ring core (master %s, exact parent params, 0 added cycles); UNSIGNED until its CLAND-MACRO-1 kit signs off" % (b, mk))
        rs = lc and t["clock"].get("landing_reader_start", {}).get("branches", {}).get(b)
        if not a.no_reset_net and rs:
            hc["reset_net"] = "cland_reader_start_%s_%d" % (b, len(rs["stages"]) - 1)
        t["hard_cores"].append(hc)
        # band -> macro footprint
        old = list(v["rect_um"])
        v["rect_um"] = [ox, oy, round(ox + cw, 3), round(oy + ch, 3)]
        v["hard_core"] = inst
        v["resized_from_um"] = old
        v["resize"] = "KV-HGSPLIT-1115: hard ring child core footprint (master %s)" % mk
        for cs in lc.get("collector_local_sources", []):
            if cs.get("name") == b and isinstance(cs.get("band"), dict):
                cs["band"] = dict(v)
        # clock tap of the core clk pin (type frame)
        cp = next(q for q in M["pins"]["pins"] if q["name"] == "clk")
        px, py = CK._orient_pt(ori, cw, ch, cp["x"], cp["y"])
        t["clock"]["taps"].append(dict(name=inst + ".clk", kind="core", xy=[round(ox + TOFF[0] + px, 3), round(oy + TOFF[1] + py, 3)],
                                       insertion_ps=250.0, insertion_ff_ps=202.5,
                                       budget_owner="KV-HGSPLIT-1115: ring child core clk, target 250/202.5 ESTIMATE (same as QC ring children), re-measure from the child's own kit"))
        rows.append(dict(type=tn, bus=b, W=v["width"] + 1, status="OK", master=mk, face=f, orient=ori, origin=[ox, oy],
                         outline=[cw, ch], disp=round(best[0], 1), axis=ax, cells=(M["cells"] or int(24.9 * (v["width"] + 1)))))

    if a.move_sites:
        rects = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in t["hard_cores"] if h["module"].startswith("kv_cland")]
        cores = [(h["origin_um"][0] - 4.32, h["origin_um"][1] - 4.32, h["origin_um"][0] + h["outline_um"][0] + 4.32, h["origin_um"][1] + h["outline_um"][1] + 4.32) for h in t["hard_cores"] if not h["module"].startswith("kv_cland")]
        rr = [(x0 - 4.33, y0 - 4.33, x1 + 4.33, y1 + 4.33) for x0, y0, x1, y1 in rects]

        def bad(x, y, c=4.33):
            return (any(a0 < x < a1 and b0 < y < b1 for a0, b0, a1, b1 in [(r0 - c + 4.33, r1 - c + 4.33, r2 + c - 4.33, r3 + c - 4.33) for r0, r1, r2, r3 in rr] + cores) or not (4.32 <= x <= W_ - 4.32 and 4.32 <= y <= H_ - 4.32))
        moved = [0]

        def fix(o):
            if isinstance(o, dict):
                kk = "xy_um" if "xy_um" in o else "xy"
                clr = 8.65 if tapset[0] else 4.33
                if kk in o and isinstance(o[kk], list) and len(o[kk]) == 2 and bad(*o[kk], clr):
                    x, y = o[kk]; found = None
                    for r in range(1, 150):
                        for dx in range(-r, r + 1):
                            for dy in ((-r, r) if abs(dx) != r else range(-r, r + 1)):
                                nx, ny = x + dx * 2.16, y + dy * 2.16
                                if not bad(nx, ny, clr):
                                    found = (nx, ny); break
                            if found:
                                break
                        if found:
                            break
                    if found:
                        o[kk] = [round(found[0], 3), round(found[1], 3)]; moved[0] += 1
                for v in o.values():
                    fix(v)
            elif isinstance(o, list):
                for v in o:
                    fix(v)
        tapset = [False]
        for k in ("landing_reader_start", "landing_writer_start", "landing_raw_branches"):
            if k in t["clock"]:
                fix(t["clock"][k])
        fix(t["clock"].get("landing_contract", {}).get("collector_tree", {}))
        tapset[0] = True
        fix(t["clock"].get("added_taps") or [])
        print("moved start/raw sites", tn, moved[0], flush=True)

(out / "plan_c.json").write_text(json.dumps(plan, indent=1) + "\n")
with open(out / "hgsplit_rows.tsv", "w") as fh:
    fh.write("type\tbus\tW\tstatus\tmaster\tface\torient\torigin\toutline\tdisp_um\tring_cells\n")
    for r in rows:
        fh.write("\t".join(str(r.get(k, "")) for k in ("type", "bus", "W", "status", "master", "face", "orient", "origin", "outline", "disp", "cells")) + "\n")
print("rings", len(rows), "ok", sum(1 for r in rows if r["status"] == "OK"), "bad", [r for r in rows if r["status"] != "OK"][:5])
