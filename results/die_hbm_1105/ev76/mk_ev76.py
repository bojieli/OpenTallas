#!/usr/bin/env python3
"""DIE-HBM-75 HBM plan event ev76 (COORD 11-05 17:20 (4): dma_m6c 2 strikes -> conservative form; outline from
HBM-FORM-TIMING-6+CONG-7 17:29 ESTIMATE).  mk_ev76.py PLAN_DIR(plain die_plan.json + core_macros.json)
 (1) ot_hgi_dma_back_static_vp4_banks_cp 300.456x275.4 -> 372.6x275.4 (util <= 0.45: 46,121 um2 / 0.45 = 102.5k um2),
     grown on the core's local E.  The pin table has NO E-face pin (N 2420 / W 2192 / S 325 + clk/rst_n inside), so every
     pin keeps its core-frame position: the new pins file is the old one byte-for-byte under a new name.  In the parent
     all four instances keep their origin and grow toward parent E (u_hb_dbk_Q__q0 R0: local E = parent E; q1 MY: the box
     [ox, ox+w] grows to ox+372.6, and since MY maps x -> ox + w - x every q1 pin and its centre clock entry move +72.144 um
     parent-E).  core_macros.json: same 10 macros, outline only.
 (2) q1 clock taps (clock.taps kind core, MY/R180 instances): xy x += 72.144 (= the same in-core centre entry).
 (3) q_hub_nw C25c reserved boot-packet bank u_host_boot_hop12 (rect 7490.88..7508.16 x 717.12..734.4) lies in the new q1
     strip: moved to just S of the core, x unchanged, y 682.56..699.84 (8.64 lattice; hop11->hop12 311 um, hop12->hop13
     311 um, both < 400).
 (4) internal_stations registers in the new boxes: re-sited with ft_nudge.nudge_explicit (a free register stays; one inside
     a box moves to the nearest free box side / grid point <= 150 um that minimises the worst hop touching a moved
     register).  Boxes: placement_boxes + 1.08 keep-off, grown by the register cell on the low sides (the cell is LL at the
     point), plus the clock-buffer halos, exactly the obstacle set ft_nudge uses.
 ft slot stations in the strips (2 regs per q0) are left to ft_nudge.py, run after this script by run_ev76.sh."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[3] / "tools" / "die_plan"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import check as C  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points, nudge_explicit, inside  # noqa: E402

pd = Path(sys.argv[1])
D = json.loads((pd / "die_plan.json").read_text()); PT = D["partition_types"]
M = "ot_hgi_dma_back_static_vp4_banks_cp"; W0, W1, H = 300.456, 372.6, 275.4; DW = round(W1 - W0, 4)
REP = dict(event="ev76", module=M, outline=[[W0, H], [W1, H]], instances=[], taps=[], channels=[], istations=[])
old_pf = None
for tn, t in PT.items():
    for h in t.get("hard_cores") or []:
        if h["module"] != M:
            continue
        assert h["outline_um"] == [W0, H], (tn, h["inst"], h["outline_um"])
        old_pf = old_pf or h["pins_file"]; assert h["pins_file"] == old_pf
        new_pf = "cores/%s__%gx%g__ev76_cons.json" % (M, W1, H)
        h["outline_um"] = [W1, H]; h["pins_file"] = new_pf
        h["note"] = (h.get("note", "") + " | ev76: conservative form %gx%g (+%g local E, COORD 17:20 (4))" % (W1, H, DW)).strip(" |")
        o = h.get("orient", "R0")
        REP["instances"].append(dict(type=tn, inst=h["inst"], orient=o, origin=h["origin_um"]))
        if o in ("MY", "R180"):
            for tp in (t.get("clock") or {}).get("taps") or []:
                if tp.get("kind") == "core" and tp.get("name") == h["inst"]:
                    x0 = tp["xy"][0]; tp["xy"] = [round(x0 + DW, 4), tp["xy"][1]]
                    tp["note"] = (tp.get("note", "") + " | ev76: +%g parent-E with the MY core's local-E growth" % DW).strip(" |")
                    REP["taps"].append(dict(type=tn, tap=tp["name"], x=[x0, tp["xy"][0]]))
# (1) pins file: identical pins, new outline name
src = pd / old_pf
pins = json.loads(src.read_text())
assert not any(abs(q["x"] - W0) < 1.0 for q in pins), "an E-face pin exists"
(pd / ("cores/%s__%gx%g__ev76_cons.json" % (M, W1, H))).write_text(src.read_text())
REP["pins"] = dict(from_=old_pf, n=len(pins), moved=0)
cm = json.loads((pd / "core_macros.json").read_text())
cm["cores"][M]["outline_um"] = [W1, H]
cm["cores"][M]["basis"] = cm["cores"][M].get("basis", "") + " | ev76 (DIE-HBM-75, COORD 11-05 17:20 (4)): conservative form +72.144 um local E (util <= 0.45), same macros"
(pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
# (3) boot channel
for c in PT["q_hub_nw"].get("channels") or []:
    if "u_host_boot_hop12;" in c.get("reason", ""):
        old = c["rect_um"]; c["rect_um"] = [7490.88, 682.56, 7508.16, 699.84]
        c["reason"] += " | ev76: moved S of u_hb_dbk_Q__q1 (was %s, inside its +72 um strip)" % old
        REP["channels"].append(dict(type="q_hub_nw", chan="u_host_boot_hop12", rect=[old, c["rect_um"]]))
# (5) COORD 11-05 17:5x: pcol_l (ot_hbm_su_pcol_l) is signed off (tag-i re-sign, eco i3) on the part-26 lane-only pin
#     table (545/565 pins +101.52 um core-x vs d44v_split, same outline 257.04x423.36): adopt that signed table.
#     The file content = d44v_split entries (w/h kept) with layer/x/y from the kit's plan_pins.json.
PC = "ot_hbm_su_pcol_l"; PCF = "cores/ot_hbm_su_pcol_l__257.04x423.36__p26_signed.json"
sig = {q["name"]: q for q in json.loads((Path(__file__).resolve().parent / "pcol_l_i3_plan_pins.json").read_text())["pins"]}
old_pc = None; npc = 0
for tn, t in PT.items():
    for h in t.get("hard_cores") or []:
        if h["module"] == PC:
            assert h["outline_um"] == [257.04, 423.36]; old_pc = old_pc or h["pins_file"]; assert h["pins_file"] == old_pc
            h["pins_file"] = PCF; npc += 1
            h["note"] = (h.get("note", "") + " | ev76: signed p26 pin table (pcol_l i3, COORD 11-05)").strip(" |")
op = json.loads((pd / old_pc).read_text()); assert {q["name"] for q in op} == set(sig)
nmv = 0
for q in op:
    g = sig[q["name"]]; nmv += (abs(q["x"] - g["x"]) > 1e-6 or abs(q["y"] - g["y"]) > 1e-6)
    q["x"], q["y"], q["layer"] = g["x"], g["y"], g["layer"]
(pd / PCF).write_text(json.dumps(op, indent=1) + "\n")
REP["pcol_l"] = dict(from_=old_pc, to=PCF, instances=npc, pins=len(op), moved=nmv)
# (4) internal stations
for tn in sorted({i["type"] for i in REP["instances"]}):
    t = PT[tn]; w, hgt = t["outline_um"]
    cw, ch = CELL_DEFAULT
    boxes = [(a - KEEPOFF - cw, b - KEEPOFF - ch, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in placement_boxes(t).values()]
    hh = C.CLOCK_BUF_HALO_UM + 0.01
    boxes += [(q[0] - hh - cw, q[1] - hh - ch, q[0] + hh, q[1] + hh) for q in clock_points(t)]
    for c in t.get("channels") or []:
        a, b, cc, d = c["rect_um"]; boxes.append((a - cw, b - ch, cc, d))
    # only registers inside the NEW strips move (pre-existing station-in-core rows elsewhere are not this event's)
    strips = []
    for h in t["hard_cores"]:
        if h["module"] == M:
            ox, oy = h["origin_um"]
            strips.append((ox + W0 - KEEPOFF - cw, oy - KEEPOFF - ch, ox + W1 + KEEPOFF, oy + H + KEEPOFF))
    for k, s in enumerate(t.get("internal_stations") or []):
        regs = s.get("regs_um") or []
        if not any(inside(r, strips) for r in regs):
            continue
        # re-site each contiguous run of strip registers between its kept neighbours (or the from/to anchors), against
        # the full obstacle set; registers outside the strips (incl. any pre-existing in-core ones) are not touched
        mv = [inside(r, strips) for r in regs]; new = [list(r) for r in regs]; worst = smax = 0.0; a = 0
        while a < len(regs):
            if not mv[a]:
                a += 1; continue
            b = a
            while b + 1 < len(regs) and mv[b + 1]:
                b += 1
            A = regs[a - 1] if a else s["from_um"]; B = regs[b + 1] if b + 1 < len(regs) else s["to_um"]
            run, wv, sv = nudge_explicit(regs[a:b + 1], boxes, w, hgt, A, B)
            for ms, stp in ((300.0, 4.32), (450.0, 4.32)):   # hop > 405 (hub reach): widen the search before giving up
                if wv <= 405.0:
                    break
                r2 = nudge_explicit(regs[a:b + 1], boxes, w, hgt, A, B, max_slide=ms, step=stp)
                if r2[1] < wv - 0.05:
                    run, wv, sv = r2
            a0, b0 = a, b
            while wv > 405.0 and (a0 > 0 or b0 + 1 < len(regs)) and b0 - a0 < b - a + 4:
                # still over the hub reach: let the kept neighbours on both sides move too (forced re-site via a
                # zero-size obstacle at each of them would be wrong; nudge_explicit only moves centres in a box, so
                # give it a box that covers just those neighbour points)
                a0 = max(0, a0 - 1); b0 = min(len(regs) - 1, b0 + 1)
                A2 = regs[a0 - 1] if a0 else s["from_um"]; B2 = regs[b0 + 1] if b0 + 1 < len(regs) else s["to_um"]
                pin = [(r[0] - .5, r[1] - .5, r[0] + .5, r[1] + .5) for r in regs[a0:b0 + 1] if not inside(r, strips)]
                r2 = nudge_explicit(regs[a0:b0 + 1], boxes + pin, w, hgt, A2, B2, max_slide=300.0, step=4.32)
                if r2[1] < wv - 0.05:
                    run, wv, sv = r2; a, b = a0, b0
            new[a:b + 1] = run; worst = max(worst, wv); smax = max(smax, sv); a = b + 1
        nm = sum(1 for a, b in zip(regs, new) if a != b)
        s["regs_um"] = new
        s["note"] = (s.get("note", "") + " | ev76: %d station(s) re-sited off a hard core" % nm).strip(" |")
        REP["istations"].append(dict(type=tn, k=k, conn=s.get("conn"), moved=nm, max_hop_moved_um=round(worst, 1),
                                     max_slide_um=round(smax, 1)))
D["note"] = "DIE-HBM-75 ev76 <- " + D.get("note", "")[:200]
(pd / "die_plan.json").write_text(json.dumps(D) + "\n")
(pd / "ev76_ledger.json").write_text(json.dumps(REP, indent=1) + "\n")
print(json.dumps(dict(instances=len(REP["instances"]), taps=REP["taps"], channels=len(REP["channels"]),
                      istations=len(REP["istations"]), pcol_l=REP["pcol_l"], regs_moved=sum(x["moved"] for x in REP["istations"]),
                      worst_moved_hop=max([x["max_hop_moved_um"] for x in REP["istations"]] or [0]),
                      max_slide=max([x["max_slide_um"] for x in REP["istations"]] or [0]))))
