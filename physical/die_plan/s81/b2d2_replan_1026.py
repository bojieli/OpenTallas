#!/usr/bin/env python3
"""PATH-S81-R3 D-S81-B2 item 1b (10-26): bk_sel option B (COORD RULING bk_sel 06:17) + 12.8 centre clock entries.

bk_sel__t2_phy1026_bk_sel: dsdv_bksel_q re-cut 648x648 -> 864x483.84 um (same area class, 0 added cycles, M5 ceiling,
new plan slice cores/bksel_q_r864/{dsdv_bksel_q.json,.lef}); vertical cut in the existing 2885.76x1226.88 slot:
  S row  q0 R0 | q1 MY          (y 8.64)
  middle u_g R0 | u_c R0        (y 501.12; u_c straddles the q0/q1 seam; u_g within 405 um of u_tx and all four q; u_c vd -> W face = pin delta of the u_c 12.8 rebuild, the current view cannot be MY on track)
  N row  q2 MX | q3 R180        (y 682.56, top 1166.4)
  u_tx at the SW corner (8.64, 8.64) next to its tl_o0 (W) and xtier_o0 (S) windows.
q pins: u_c bundle (t_o/t_s/f_c/f_cr, 1286 b) on M5 (every 3rd track) at frame x 405-590 of the N face, lane (515 b) on M5 at x 648-846
(nearest u_g for q0, mirrored for q1); ck + rst at the core centre (12.8a centre entry, M5; island M9->M5 stack).
12.8 (and COORD 06:5x gunit spot-check): every 'early' core tap in the plan is RETIRED -> clock.core_taps removed; each
hard core of the type gets a plan-record centre clock entry (kind core, xy = core geometric centre, insertion = die
common latency 250 TT / 202.5 FF); the parent tap_um moves to the partition clock centre = the channel lattice point nearest the centroid of the core entries.  Cores whose current views
have an edge clock pin or a different latency are handed to S81-CORE-LAT for the structured rebuild (ledger list).

usage: b2d2_replan_1026.py REPO PLAN_IN PLAN_OUT LEDGER
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
PLAN_IN, PLAN_OUT, LEDGER = map(Path, sys.argv[2:5])
sys.path[:0] = [str(REPO), str(REPO / "tools" / "die_plan"), str(REPO / "physical" / "die_plan" / "s81")]
import ft_corridor as F  # noqa: E402
import check as C  # noqa: E402

BK, GU = "bk_sel__t2_phy1026_bk_sel", "gunit__t1_phy1026_gunit"
G = 8.64
plan_dir = REPO / "physical" / "die_plan" / "s81"
raw = json.loads(PLAN_IN.read_text())
T = raw["partition_types"]
LAY = F.S.Plan(raw, PLAN_IN).layers
led = dict(tool="physical/die_plan/s81/b2d2_replan_1026.py", plan_in=PLAN_IN.name, bk_sel={}, clock_128={})

# ------------------------------------------------------------------ re-cut q slice (pins + abstract LEF)
QW, QH = 864.0, 483.84
SL = plan_dir / "cores" / "bksel_q_r864"
SL.mkdir(parents=True, exist_ok=True)
old = json.loads((plan_dir / "inputs" / "core_pins" / "dsdv_bksel_q.json").read_text())["pins"]
grp = {}
for p in old:
    grp.setdefault(p["name"].split("[")[0], []).append(p["name"])


def bitkey(n):
    return int(n.split("[")[1].rstrip("]")) if "[" in n else 0


pins = []
yN = round(QH - 0.132, 3)
x = 403.224                       # M5 track (offset 0.024, pitch 0.048); one vertical layer so MY/R180 stay on track
for g in ("t_o", "t_s", "f_c", "f_cr"):
    for n in sorted(grp[g], key=bitkey):
        pins.append(dict(name=n, layer="M5", x=round(x, 3), y=yN))
        x += 0.144
assert x < 640, x
x = 648.024                       # M5 track (offset 0.024, pitch 0.048)
for n in sorted(grp["lane"], key=bitkey):
    pins.append(dict(name=n, layer="M5", x=round(x, 3), y=yN))
    x += 0.384
assert x < QW - 8, x
pins.append(dict(name="ck", layer="M5", x=432.024, y=241.92))   # 12.8a centre clock entry
pins.append(dict(name="rst", layer="M5", x=440.664, y=241.92))  # regional reset relay in the same island
assert len(pins) == len(old), (len(pins), len(old))
pj = dict(module="dsdv_bksel_q", lef="physical/die_plan/s81/cores/bksel_q_r864/dsdv_bksel_q.lef",
          source="PATH-S81-R3 10-26 plan slice for the option-B re-cut (864x483.84, M5 ceiling); no view yet",
          pins=pins)
(SL / "dsdv_bksel_q.json").write_text(json.dumps(pj, indent=0) + "\n")
lef = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "MACRO dsdv_bksel_q", "  CLASS BLOCK ;",
       "  ORIGIN 0 0 ;", f"  SIZE {QW} BY {QH} ;"]
for p in pins:
    w = 0.018 if p["layer"] == "M3" else 0.024
    d = "INPUT" if p["name"].split("[")[0] in ("ck", "rst", "f_c", "f_cr", "lane") else "OUTPUT"
    lef += [f"  PIN {p['name']}", f"    DIRECTION {d} ;", "    USE " + ("CLOCK" if p["name"] == "ck" else "SIGNAL") + " ;",
            "    PORT", f"      LAYER {p['layer']} ;",
            f"        RECT {p['x'] - w:.3f} {p['y'] - 0.1:.3f} {p['x'] + w:.3f} {p['y'] + 0.1:.3f} ;", "    END",
            f"  END {p['name']}"]
lef += ["  OBS"] + [f"    LAYER M{k} ;\n      RECT 0 0 {QW} {QH} ;" for k in range(1, 6)] + ["  END", "END dsdv_bksel_q",
                                                                                     "END LIBRARY"]
(SL / "dsdv_bksel_q.lef").write_text("\n".join(lef) + "\n")


def solve_offset(hc):
    cw, ch = hc["outline_um"]
    pp_all = C.core_pins(hc, plan_dir)
    res = []
    for axis, d in ((0, "V"), (1, "H")):
        pp = [(ln, (x_, y_)) for _n, ln, x_, y_ in pp_all if ln in LAY and ln != "M1" and LAY[ln]["dir"] == d]
        base = hc["origin_um"][axis]
        for k in range(0, int(round(F.S.BASE_LATTICE_UM / 0.001))):
            dd = round(k * 0.001, 3)
            if all(C.on_track(base + dd + C._orient_pt(hc["orient"], cw, ch, *xy)[axis], LAY[ln]) for ln, xy in pp):
                res.append(dd)
                break
        else:
            raise SystemExit(f"no track offset for {hc['inst']} {hc['orient']} axis {axis}")
    return res


# ------------------------------------------------------------------ bk_sel layout
t = T[BK]
W, H = t["outline_um"]
Y_M, Y_N = G + QH + G, G + QH + G + 172.8 + G          # 501.12, 682.56
X_Q0, X_Q1 = 648.0, 648.0 + QW + G                     # 648.0, 1520.64
place = {"u_bk_sel.u_tx": ((G, G), "R0"),
         "u_bk_sel.u_sel.g_q[0].u_q": ((X_Q0, G), "R0"), "u_bk_sel.u_sel.g_q[1].u_q": ((X_Q1, G), "MY"),
         "u_bk_sel.u_sel.g_q[2].u_q": ((X_Q0, Y_N), "MX"), "u_bk_sel.u_sel.g_q[3].u_q": ((X_Q1, Y_N), "R180"),
         "u_bk_sel.u_sel.u_g": ((1002.24, Y_M), "R0"), "u_bk_sel.u_sel.u_c": ((1261.44, Y_M), "R0")}
rows = []
for hc in t["hard_cores"]:
    o, orient = place[hc["inst"]]
    frm = dict(origin=hc["origin_um"], outline=hc["outline_um"], orient=hc.get("orient", "R0"))
    if hc["module"] == "dsdv_bksel_q":
        hc.update(outline_um=[QW, QH], lef="physical/die_plan/s81/cores/bksel_q_r864/dsdv_bksel_q.lef",
                  pins_file="cores/bksel_q_r864/dsdv_bksel_q.json", obs_max="M5")
    hc["origin_um"] = [round(o[0], 4), round(o[1], 4)]
    hc["orient"] = orient
    for v in hc["origin_um"]:
        assert abs(v / G - round(v / G)) < 1e-6, (hc["inst"], v)
    hc["track_offset_um"] = solve_offset(hc)
    rows.append(dict(inst=hc["inst"], frm=frm, to=dict(origin=hc["origin_um"], outline=hc["outline_um"],
                                                       orient=orient, track_offset_um=hc["track_offset_um"])))
bx = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
       h["origin_um"][1] + h["outline_um"][1], h["inst"]) for h in t["hard_cores"]]
for i, a in enumerate(bx):
    assert a[2] <= W - G + 1e-6 and a[3] <= H - G + 1e-6, a
    for b in bx[i + 1:]:
        gx, gy = max(b[0] - a[2], a[0] - b[2]), max(b[1] - a[3], a[1] - b[3])
        assert gx >= G - 1e-6 or gy >= G - 1e-6, (a, b)
dist = {}
for a in bx:
    for b in bx:
        if a[4] < b[4]:
            dx, dy = max(0, b[0] - a[2], a[0] - b[2]), max(0, b[1] - a[3], a[1] - b[3])
            dist[f"{a[4]}|{b[4]}"] = round(dx + dy, 2)
led["bk_sel"] = dict(cores=rows, box_manhattan_um=dist)
t["note"] = t.get("note", "") + ("; PATH-S81-R3 D-S81-B2 10-26: COORD option B, q re-cut 864x483.84 vertical cut "
                                 "(S q0/q1, middle u_g+u_c, N q2/q3), u_tx SW corner, 12.8 centre clock entries")

# ------------------------------------------------------------------ 12.8: retire every early core tap
LAT_TT = float(raw["clock"]["common_latency_ps"])
for tn, tt in T.items():
    ck = tt.get("clock") or {}
    if ck.get("core_taps") != "early" and tn not in (BK, GU):
        continue
    w, h = tt["outline_um"]
    retired = [dict(name=tp["name"], xy=tp["xy"], insertion_ps=tp.get("insertion_ps"))
               for tp in ck.get("taps", []) if tp.get("kind") == "core"]
    keep = [tp for tp in ck.get("taps", []) if tp.get("kind") != "core"]
    ck.pop("core_taps", None)
    entries = []
    for hc in tt.get("hard_cores", []):
        (ox, oy), (cw, ch) = hc["origin_um"], hc["outline_um"]
        entries.append(dict(name=hc["inst"], kind="core", xy=[round(ox + cw / 2, 4), round(oy + ch / 2, 4)],
                            insertion_ps=LAT_TT, insertion_tol_ps=20.0,
                            budget_owner="PATH-S81 (S81 clock owner, 12.9a); rebuild S81-CORE-LAT",
                            note="12.8a plan-defined centre clock entry (clock/reset island, M9->M5 stack); die common "
                                 "latency 250 TT (12.3); early tap retired (12.8d)"))
    ck["taps"] = keep + entries
    old_tap = ck.get("tap_um")
    # partition clock centre: the lattice point outside every hard core (>= 2 um clear, i.e. a channel / std-cell
    # island site) nearest the centroid of the core clock entries (the partition centre when the type has no cores)
    if entries:
        gx = sum(e["xy"][0] for e in entries) / len(entries)
        gy = sum(e["xy"][1] for e in entries) / len(entries)
    else:
        gx, gy = w / 2, h / 2
    hb = [(hc["origin_um"][0] - 2, hc["origin_um"][1] - 2, hc["origin_um"][0] + hc["outline_um"][0] + 2,
           hc["origin_um"][1] + hc["outline_um"][1] + 2) for hc in tt.get("hard_cores", [])]
    best = None
    step = 4.32
    for i in range(1, int(w / step)):
        for j in range(1, int(h / step)):
            px, py = i * step, j * step
            if any(b[0] <= px <= b[2] and b[1] <= py <= b[3] for b in hb):
                continue
            d = abs(px - gx) + abs(py - gy)
            if best is None or d < best[0]:
                best = (d, px, py)
    ck["tap_um"] = [round(best[1], 4), round(best[2], 4)]
    tt["clock"] = ck
    led["clock_128"][tn] = dict(retired_early=retired, centre_entries=len(entries), parent_tap_from=old_tap,
                                parent_tap_to=ck["tap_um"])

PLAN_OUT.write_text(json.dumps(raw, separators=(",", ":")) + "\n")
LEDGER.write_text(json.dumps(led, indent=1) + "\n")
print(json.dumps(dist, indent=0))
print("types with retired early taps / centre entries:", len(led["clock_128"]))
