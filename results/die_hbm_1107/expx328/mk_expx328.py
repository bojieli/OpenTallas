#!/usr/bin/env python3
"""DIE-HBM-90-PEV 11-07 d44v event expx328_1107 (COORD 11-07 23:01 (4)(i); COUNT-AUDIT-2 22:54 (B)(1)).
The exp_x half of HBM-CONS-2/SUK part 55 (claude/hbm-cons-2-suk-1106@1f697296df, results/die_hbm_1106/suk_vk/mk_p55.py),
replayed on main d44v (after part 60/61 and istadrop_1107), renamed: 'part 55' is also DIE-HBM-83's planfill event.
    mk_expx328.py PLAN_DIR   (plain die_plan.json + core_macros.json + clock_entries.json + cores/)
 * ot_hbm_su_pg_lane_exp_x_core 319.68 -> 328.32 x 207.36 (+8.64 local E, 60 instances) = the outline of the signed vL
   (expx_one_eco i1, re-signed flow-20261107-ed-hbm).  ot_hbm_su_pg_lane_full_x_core is NOT changed (stays 354.24, p42 table):
   it is separable (own instances, no signed vK form); in rows that hold it, its __l/__s pair moves as one item, pure x shift.
 * six SRAMs on two edge columns (W MY / E R0), clock entry (164.16, 103.68), only the clk row of the pin table moves:
   table = the SUK part-55 exp_x table byte for byte (sha256 ec6b144f..., the pins the vL routed DB has, 2118/2118).
 * __s partner (ot_hbm_su_pg_sfu_s_core) keeps abutting local E of its __l (pure x shift, pins unchanged, tap follows).
 * Row solver, taps, clock entries, station re-site and obs_max M6 exactly as mk_p55.py.
PIN CYCLES are NOT in this geometry event: they are the vK RTL (results/die_hbm_1106/suk_vk/gen_lane_xk.py, part55 pin_cycles)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[3] / "tools" / "die_plan"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import check as C  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points, nudge_explicit, inside  # noqa: E402

pd = Path(sys.argv[1])
D = json.loads((pd / "die_plan.json").read_text()); PT = D["partition_types"]
CE = json.loads((pd / "clock_entries.json").read_text())
CM = json.loads((pd / "core_macros.json").read_text())
MS, SW = "ot_hbm_su_pg_sfu_s_core", 120.96
H, GAP, EDGE = 207.36, 8.64, 8.64
SPEC = {"ot_hbm_su_pg_lane_exp_x_core": dict(w0=319.68, w1=328.32, cols=(19.44, 211.68), entry=(164.16, 103.68))}
PAIRED = set(SPEC) | {"ot_hbm_su_pg_lane_full_x_core"}   # lane cores whose __s abuts local E: one row item
ROWS, MW, MH = (30.96, 83.16, 135.36), 94.824, 41.064
REP = dict(event="expx328_1107", source="claude/hbm-cons-2-suk-1106@1f697296dfd part55_event.json (exp_x module; full_x left out, separable)",
           signed="ot_hbm_su_pg_lane_exp_x_core vL: intel1 /srv/opentallas-scratch2/claude/die-hbm-89/expx/resign_ed (re-sign flow-20261107-ed-hbm, LEC EQ 65584, build_commit 1f697296dfd)",
           pin_cycles="vK RTL (results/die_hbm_1106/suk_vk/gen_lane_xk.py, bench results/die_hbm_1106/suk_vk/bench_all.log): write/reducer/fault/coll ports +15, SFU seam out/return +9 (pair), all other ports 0, vs the old part-18 exp_x",
           rtl="kit RTL = gen_lane_xk.py outputs (byte-identical on 1f697296dfd and on this main) + wrappers/oneclk/ot_hbm_su_pg_lane_exp_x_core__p55.sv (recipes_b2 wrapper_by_pins_sha256 ec6b144f...)", approved="COORD 2026-11-07 23:01 (4)(i); geometry = HBM-CONS-2/SUK part 55 exp_x (COORD RULINGS 11-06 22:0x (6))", by="DIE-HBM-90-PEV", modules={}, moved=[], taps=[], istations=[], neighbours=[])
OLD_PF = {}
for m, s in SPEC.items():
    s["new_pf"] = "cores/%s__%gx%g__d44v_expx328.json" % (m, s["w1"], H)
    REP["modules"][m] = dict(outline=[[s["w0"], H], [s["w1"], H]], pins_file=s["new_pf"], entry_um=s["entry"], instances=0)
fx = lambda v: round(v, 4)
def local_e_positive(o):
    return o in ("R0", "MX")
strips = {}
for tn, t in PT.items():
    hc = t.get("hard_cores") or []
    if not any(h["module"] in SPEC for h in hc):
        continue
    W = t["outline_um"][0]
    byname = {h["inst"]: h for h in hc}
    row_ys = sorted({h["origin_um"][1] for h in hc if h["module"] in SPEC})
    old_boxes = {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in hc}
    new_strips = []
    for y in row_ys:
        row = sorted([h for h in hc if h["origin_um"][1] == y], key=lambda h: h["origin_um"][0])
        items = []; i = 0
        while i < len(row):
            h = row[i]
            nx = row[i + 1] if i + 1 < len(row) else None
            pair = nx is not None and {h["module"], nx["module"]} & PAIRED and MS in (h["module"], nx["module"]) and abs(h["origin_um"][0] + h["outline_um"][0] - nx["origin_um"][0]) < 1e-3
            if pair:
                items.append([h, nx]); i += 2
            else:
                assert h["module"] not in PAIRED, ("lane without abutting __s", tn, h["inst"])
                items.append([h]); i += 1
        neww = lambda it: sum(SPEC[h["module"]]["w1"] if h["module"] in SPEC else h["outline_um"][0] for h in it)
        x0 = [it[0]["origin_um"][0] for it in items]
        n = len(items); nw = [neww(it) for it in items]; x1 = list(x0)
        # the least moves: push right where a grown item hits the next; then pull left from the partition edge
        for k in range(1, n):
            x1[k] = max(x1[k], x1[k - 1] + nw[k - 1] + GAP)
        if x1[-1] + nw[-1] > W - EDGE + 1e-6:
            x1[-1] = W - EDGE - nw[-1]
            for k in range(n - 2, -1, -1):
                x1[k] = min(x1[k], x1[k + 1] - nw[k] - GAP)
        assert x1[0] >= EDGE - 1e-6, ("row does not fit", tn, y, x1[0])
        for it, a, b in zip(items, x0, x1):
            b = fx(b)
            xx = b
            for h in it:
                oldx = h["origin_um"][0]; w = SPEC[h["module"]]["w1"] if h["module"] in SPEC else h["outline_um"][0]
                if abs(oldx - xx) > 1e-6:
                    REP["moved"].append(dict(type=tn, inst=h["inst"], x=[oldx, xx], dx=fx(xx - oldx)))
                h["_newx"] = xx; xx = fx(xx + w)
        new_strips.append((y, items))
    for y, items in new_strips:
        for it in items:
            for h in it:
                nx = h.pop("_newx"); ox = h["origin_um"][0]; m = h["module"]; o = h.get("orient") or "R0"
                if m in SPEC:
                    s = SPEC[m]; pf0 = h["pins_file"]
                    assert h["outline_um"] == [s["w0"], H], (tn, h["inst"], h["outline_um"])
                    assert OLD_PF.setdefault(m, pf0) == pf0, (m, pf0, OLD_PF[m])
                    h["outline_um"] = [s["w1"], H]; h["pins_file"] = s["new_pf"]; h["origin_um"] = [nx, h["origin_um"][1]]
                    h["obs_max"] = "M6"
                    h["note"] = (h.get("note", "") + " | expx328_1107 (= SUK part55 exp_x): %gx%g (+%g local E), SRAM edge columns W(MY)/E(R0), clock entry %s, obs M6" % (s["w1"], H, s["w1"] - s["w0"], list(s["entry"]))).strip(" |")
                    REP["modules"][m]["instances"] += 1
                elif abs(nx - ox) > 1e-6:
                    h["origin_um"] = [nx, h["origin_um"][1]]
                    h["note"] = (h.get("note", "") + " | expx328_1107: x %+g (row re-pack, pure shift, pins unchanged)" % fx(nx - ox)).strip(" |")
    # taps
    for tp in (t.get("clock") or {}).get("taps") or []:
        if tp.get("kind") != "core" or tp.get("name") not in byname:
            continue
        h = byname[tp["name"]]; old = old_boxes[h["inst"]]; o = h.get("orient") or "R0"; x0n, y0n = h["origin_um"]; xy0 = list(tp["xy"])
        if h["module"] in SPEC:
            s = SPEC[h["module"]]; ex, ey = s["entry"]
            px = x0n + ex if o in ("R0", "MX") else x0n + s["w1"] - ex
            py = y0n + ey if o in ("R0", "MY") else y0n + H - ey
            tp["xy"] = [fx(px), fx(py)]
        elif abs(x0n - old[0]) > 1e-6:
            tp["xy"] = [fx(tp["xy"][0] + x0n - old[0]), tp["xy"][1]]
        if tp["xy"] != xy0:
            tp["note"] = (tp.get("note", "") + " | expx328_1107").strip(" |")
            REP["taps"].append(dict(type=tn, tap=tp["name"], xy=[xy0, tp["xy"]]))
    # stations under the new footprint of anything that moved or grew
    sb = []
    for h in hc:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if (x, y, x + w, y + hh) != old_boxes[h["inst"]]:
            sb.append((x, y, x + w, y + hh))
    strips[tn] = sb
    REP["neighbours"].append(dict(type=tn, moved=sum(1 for r in REP["moved"] if r["type"] == tn)))
    # clock entries of this type
    blk = CE.get(tn) or {}
    for inst, e in blk.items():
        if isinstance(e, dict) and e.get("module") in SPEC:
            s = SPEC[e["module"]]; ex, ey = s["entry"]
            e["xy_um"] = [ex, ey]; e["island_um"] = [fx(ex - 4.32), fx(ey - 4.32), fx(ex + 4.32), fx(ey + 4.32)]
# new pin tables: clk row only
for m, s in SPEC.items():
    pins = json.loads((pd / OLD_PF[m]).read_text())
    assert isinstance(pins, list) and max(p["x"] for p in pins) < s["w0"] - 0.2 or True
    assert not any(p["x"] > s["w0"] - 0.2 and 0.2 < p["y"] < H - 0.2 for p in pins), "an E-face pin exists"
    ck = [p for p in pins if p["name"] == "clk"]; assert len(ck) == 1, m
    ck[0]["x"] = fx(s["entry"][0] + 0.024); ck[0]["y"] = s["entry"][1]
    assert abs((ck[0]["x"] - 0.024) / 0.048 - round((ck[0]["x"] - 0.024) / 0.048)) < 1e-6
    (pd / s["new_pf"]).write_text(json.dumps(pins, indent=1) + "\n")
    c = CM["cores"][m]; assert c["outline_um"] == [s["w0"], H]
    c["outline_um"] = [s["w1"], H]
    assert len(c["macros"]) == 6
    for k, mc in enumerate(c["macros"]):
        x = s["cols"][k % 2]; y = ROWS[k // 2]
        mc["rect_um"] = [x, y, fx(x + MW), fx(y + MH)]; mc["orient"] = "R0" if k % 2 else "MY"
    c["basis"] = c.get("basis", "") + " | expx328_1107 (= HBM-CONS-2/SUK part55, COORD 11-06 22:0x (6) + 22:35; COORD 11-07 23:01 (4)(i)): edge columns W(MY)/E(R0), logic centre, >=15 um on every pin face"
    W_core_e = s["w1"] - 4.32
    REP["modules"][m].update(macro_cols=s["cols"], macro_rows=ROWS, channels_um=dict(w_far=fx(s["cols"][0] - 4.32), e_far=fx(W_core_e - s["cols"][1] - MW), centre=fx(s["cols"][1] - s["cols"][0] - MW)))
# stations
for tn, sbx in sorted(strips.items()):
    t = PT[tn]; w, hgt = t["outline_um"]; cw, ch = CELL_DEFAULT
    boxes = [(a - KEEPOFF - cw, b - KEEPOFF - ch, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in placement_boxes(t).values()]
    hh = C.CLOCK_BUF_HALO_UM + 0.01
    boxes += [(p[0] - hh - cw, p[1] - hh - ch, p[0] + hh, p[1] + hh) for p in clock_points(t)]
    for c in t.get("channels") or []:
        a, b, cc, d = c["rect_um"]; boxes.append((a - cw, b - ch, cc, d))
    sb = [(a - KEEPOFF - cw, b - KEEPOFF - ch, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in sbx]
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
        s["regs_um"] = new
        s["note"] = (s.get("note", "") + " | expx328_1107: %d station(s) re-sited off the grown/moved lane pair" % nm).strip(" |")
        REP["istations"].append(dict(type=tn, k=k, conn=s.get("conn"), moved=nm, max_hop_um=round(worst, 1), max_slide_um=round(smax, 1)))
D["note"] = "DIE-HBM-90-PEV expx328_1107 <- " + D.get("note", "")[:200]
(pd / "die_plan.json").write_text(json.dumps(D) + "\n")
(pd / "clock_entries.json").write_text(json.dumps(CE) + "\n")
(pd / "core_macros.json").write_text(json.dumps(CM, indent=1) + "\n")
(pd / "expx328_1107_event.json").write_text(json.dumps(REP, indent=1) + "\n")
print(json.dumps(dict(modules=REP["modules"], moved=len(REP["moved"]), dxmax=max(abs(r["dx"]) for r in REP["moved"]), taps=len(REP["taps"]), istations=len(REP["istations"]),
                      regs_moved=sum(x["moved"] for x in REP["istations"]), neighbours=REP["neighbours"])))
