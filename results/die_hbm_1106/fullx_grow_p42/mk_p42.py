#!/usr/bin/env python3
"""HBM-FORM-SPLIT-13-FULLX d44v part 42 (DIE-HBM-81 12:06 (b) APPROVED): ot_hbm_su_pg_lane_full_x_core grows on its local E
319.68 x 207.36 -> 354.24 x 207.36 (+34.56, stdcell util 0.52 -> ~0.44 <= 0.45, conservative form for the vB build), and its
__s partner (ot_hbm_su_pg_sfu_s_core) that abuts it on the E side moves E by the same 34.56 (pure x shift).
    mk_p42.py PLAN_DIR   (plain die_plan.json + core_macros.json + cores/)
 Instances (4 types: q_su00, q_su00__physical_v1, q_su10, q_su10__physical_v1; R0 and MX, both keep local E = parent E):
  * u_su_Q{0,1}_lane_exp0__l: origin kept, outline 354.24 x 207.36.  The pin table has NO E-face pin (N 696 / S 896 / W 558
    + clk inside), so every pin keeps its core-frame position: the new pins file is the old one byte for byte under the new
    outline name.  Its clock tap (in-core entry, core frame unchanged) and clock_entries stay.
  * u_su_Q{0,1}_lane_exp0__s: origin x + 34.56 (q_su00: 328.32 -> 362.88, free to the E; q_su10: 838.08 -> 872.64, street to
    u_su_Q1_lane_exp2__l 43.2 -> 8.64), pins file, outline, orient unchanged; its clock tap x + 34.56.
  * core_macros.json: full_x outline only (same 6 SRAMs, same rects).
  * internal_stations registers inside the newly covered strip (E of the old __s box) are re-sited exactly as ev76 does
    (ft_nudge.nudge_explicit against the ft_nudge obstacle set); ft slot stations are left to ft_nudge.py (replay)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[3] / "tools" / "die_plan"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import check as C  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points, nudge_explicit, inside  # noqa: E402

pd = Path(sys.argv[1])
D = json.loads((pd / "die_plan.json").read_text()); PT = D["partition_types"]
ML, MS = "ot_hbm_su_pg_lane_full_x_core", "ot_hbm_su_pg_sfu_s_core"
W0, W1, H = 319.68, 354.24, 207.36; DW = round(W1 - W0, 4)
NEW_PF = "cores/%s__%gx%g__d44v_p42.json" % (ML, W1, H)
TYPES = {"q_su00": "0", "q_su00__physical_v1": "0", "q_su10": "1", "q_su10__physical_v1": "1"}
REP = dict(event="part42", module=ML, partner=MS, outline=[[W0, H], [W1, H]], shift_um=DW, instances=[], taps=[], istations=[])
old_pf = None; strips = {}
for tn, t in PT.items():
    for h in t.get("hard_cores") or []:
        if h["module"] == ML:
            assert tn in TYPES, ("full_x outside the 4 known types", tn, h["inst"])
    if tn not in TYPES:
        continue
    q = TYPES[tn]; hc = {h["inst"]: h for h in t["hard_cores"]}
    L = hc["u_su_Q%s_lane_exp0__l" % q]; S = hc["u_su_Q%s_lane_exp0__s" % q]
    assert L["module"] == ML and S["module"] == MS and L["outline_um"] == [W0, H] and S["outline_um"] == [120.96, H]
    o = L.get("orient", "R0"); assert o == S.get("orient", "R0") and o in ("R0", "MX"), (tn, o)
    lx, ly = L["origin_um"]; sx, sy = S["origin_um"]
    assert abs(lx + W0 - sx) < 1e-6 and abs(ly - sy) < 1e-6, ("__s does not abut __l on E", tn, L["origin_um"], S["origin_um"])
    old_pf = old_pf or L["pins_file"]; assert L["pins_file"] == old_pf
    # the new strip (E of the old __s box) must be free of other hard cores; street to the next core >= 8.64
    nx0, nx1 = sx + 120.96, sx + 120.96 + DW
    for h in t["hard_cores"]:
        if h is L or h is S:
            continue
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if y < ly + H and y + hh > ly:
            assert not (x < nx1 + 8.64 - 1e-6 and x + w > nx0 + 1e-6), ("strip/street hits", tn, h["inst"], x)
    L["outline_um"] = [W1, H]; L["pins_file"] = NEW_PF
    L["note"] = (L.get("note", "") + " | part42: %gx%g (+%g local E, DIE-HBM-81 12:06 (b), vB util <= 0.45)" % (W1, H, DW)).strip(" |")
    S["origin_um"] = [round(sx + DW, 4), sy]
    S["note"] = (S.get("note", "") + " | part42: x +%g with the __l grow (pure shift, pins unchanged)" % DW).strip(" |")
    REP["instances"].append(dict(type=tn, l=L["inst"], s=S["inst"], orient=o, l_origin=L["origin_um"], s_origin=[[sx, sy], S["origin_um"]]))
    nt = 0
    for tp in (t.get("clock") or {}).get("taps") or []:
        if tp.get("kind") == "core" and tp.get("name") == S["inst"]:
            x0 = tp["xy"][0]; tp["xy"] = [round(x0 + DW, 4), tp["xy"][1]]; nt += 1
            tp["note"] = (tp.get("note", "") + " | part42: +%g with its core" % DW).strip(" |")
            REP["taps"].append(dict(type=tn, tap=tp["name"], x=[x0, tp["xy"][0]]))
    assert nt == 1, (tn, nt)
    strips[tn] = (nx0, ly, nx1, ly + H)
# pins: same table, new outline name
pins = json.loads((pd / old_pf).read_text())
assert not any(p["x"] > W0 - 0.2 and 0.2 < p["y"] < H - 0.2 for p in pins), "an E-face pin exists"
assert max(p["x"] for p in pins) < W0
(pd / NEW_PF).write_text((pd / old_pf).read_text())
REP["pins"] = dict(from_=old_pf, to=NEW_PF, n=len(pins), moved=0)
cm = json.loads((pd / "core_macros.json").read_text())
assert cm["cores"][ML]["outline_um"] == [W0, H]
cm["cores"][ML]["outline_um"] = [W1, H]
cm["cores"][ML]["basis"] = cm["cores"][ML].get("basis", "") + " | part42 (HBM-FORM-SPLIT-13-FULLX, DIE-HBM-81 12:06): +34.56 um local E (util <= 0.45), same macros"
(pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
# internal stations inside the new strips (ev76 method)
for tn, st in sorted(strips.items()):
    t = PT[tn]; w, hgt = t["outline_um"]; cw, ch = CELL_DEFAULT
    boxes = [(a - KEEPOFF - cw, b - KEEPOFF - ch, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in placement_boxes(t).values()]
    hh = C.CLOCK_BUF_HALO_UM + 0.01
    boxes += [(p[0] - hh - cw, p[1] - hh - ch, p[0] + hh, p[1] + hh) for p in clock_points(t)]
    for c in t.get("channels") or []:
        a, b, cc, d = c["rect_um"]; boxes.append((a - cw, b - ch, cc, d))
    sb = [(st[0] - KEEPOFF - cw, st[1] - KEEPOFF - ch, st[2] + KEEPOFF, st[3] + KEEPOFF)]
    for k, s in enumerate(t.get("internal_stations") or []):
        regs = s.get("regs_um") or []
        if not any(inside(r, sb) for r in regs):
            continue
        mv = [inside(r, sb) for r in regs]; new = [list(r) for r in regs]; worst = smax = 0.0; a = 0
        while a < len(regs):
            if not mv[a]:
                a += 1; continue
            b = a
            while b + 1 < len(regs) and mv[b + 1]:
                b += 1
            A = regs[a - 1] if a else s["from_um"]; B = regs[b + 1] if b + 1 < len(regs) else s["to_um"]
            run, wv, sv = nudge_explicit(regs[a:b + 1], boxes, w, hgt, A, B)
            for ms, stp in ((300.0, 4.32), (450.0, 4.32)):
                if wv <= 405.0:
                    break
                r2 = nudge_explicit(regs[a:b + 1], boxes, w, hgt, A, B, max_slide=ms, step=stp)
                if r2[1] < wv - 0.05:
                    run, wv, sv = r2
            new[a:b + 1] = run; worst = max(worst, wv); smax = max(smax, sv); a = b + 1
        nm = sum(1 for x, y in zip(regs, new) if x != y)
        assert not any(inside(r, sb) for r in new), ("station still in strip", tn, k)
        s["regs_um"] = new
        s["note"] = (s.get("note", "") + " | part42: %d station(s) re-sited off the grown lane/sfu_s pair" % nm).strip(" |")
        REP["istations"].append(dict(type=tn, k=k, conn=s.get("conn"), moved=nm, max_hop_um=round(worst, 1), max_slide_um=round(smax, 1)))
D["note"] = "HBM-FORM-SPLIT-13-FULLX part42 <- " + D.get("note", "")[:200]
(pd / "die_plan.json").write_text(json.dumps(D) + "\n")
(pd / "part42_event.json").write_text(json.dumps(REP, indent=1) + "\n")
print(json.dumps(dict(instances=len(REP["instances"]), taps=REP["taps"], istations=REP["istations"],
                      regs_moved=sum(x["moved"] for x in REP["istations"]))))
