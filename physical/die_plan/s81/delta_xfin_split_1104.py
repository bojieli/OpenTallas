#!/usr/bin/env python3
"""S81 plan event XFIN-DISSOLVE (DIE-S81-56 11-04, COORD 19:2x, option A): ot_s81dv_xfin dissolved in the 16 *_C types.  Its 4 ot_s81dv_eng_finish
(signed, xfin4d) and ot_s81dv_norm_finish (FORM-NF) become hard cores, xstop and the xfin top go soft in the tile (asbuilt dissolve).  A 941.76x190.08
row of 5 replaces the 362.88x362.88 slot: order e0 e1 f e2 e3, 8.64 gaps, pin (N) face toward the tile centre (R0 up, MX down), keeps the type's orient.
    python3 delta_xfin_split_1104.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT     (cwd = repo root)
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import check as CK, schema as S, reset_tree as RT
from plan_event_1104 import plan_text, publish_tree
from placement_obstacles import placement_boxes
VIEW = "physical/die_plan/s81/cores/views/xfin_signed_1104"
W, H, G, M = 181.44, 190.08, 8.64, 34.56
RW = 5 * W + 4 * G
R = lambda v: round(v, 3)
ROW = [("g_cp[0].u_e", "ot_s81dv_eng_finish"), ("g_cp[1].u_e", "ot_s81dv_eng_finish"), ("u_f", "ot_s81dv_norm_finish"),
       ("g_cp[2].u_e", "ot_s81dv_eng_finish"), ("g_cp[3].u_e", "ot_s81dv_eng_finish")]


def offset(P, tn, row, pins):
    cw, ch = row["outline_um"]
    o, (ox, oy) = row["orient"], row["origin_um"]
    frames = [pi for pi, p in P.parts.items() if p["type"] == tn]
    def fits(axis, d):
        for name, ln, x, y in pins:
            L = P.layers.get(ln)
            if L is None or ln == "M1" or (L["dir"] == "V") != (axis == 0):
                continue
            tx, ty = CK._orient_pt(o, cw, ch, x, y)
            pt = (ox + d + tx, oy + ty) if axis == 0 else (ox + tx, oy + d + ty)
            for fx, fy in [pt] + [P.to_die(pi, pt) for pi in frames if ln not in CK.MIRROR_SKIP or P.parts[pi].get("orient", "R0") == "R0"]:
                if not CK.on_track(fx if axis == 0 else fy, L):
                    return False
        return True
    dx = next((R(k * 0.002) for k in range(0, 500) if fits(0, k * 0.002)), None)
    dy = next((R(k * 0.002) for k in range(0, 500) if fits(1, k * 0.002)), None)
    return dx, dy


def site(t, xf):
    """row site nearest the old slot centre, 8.64 um clear of every other core, room on the pin side reported"""
    rs = [c["origin_um"] + c["outline_um"] for c in t["hard_cores"] if c is not xf]
    TW, TH = t["outline_um"]
    ys = sorted({M, TH - M - H} | {r[1] + r[3] + G for r in rs} | {R(r[1] - G - H) for r in rs})
    xs = sorted({M, TW - M - RW} | {r[0] + r[2] + G for r in rs} | {R(r[0] - G - RW) for r in rs})
    cx, cy = xf["origin_um"][0] + xf["outline_um"][0] / 2, xf["origin_um"][1] + xf["outline_um"][1] / 2
    best = []
    for y in ys:
        for x in xs:
            if x < M or x + RW > TW - M or y < M or y + H > TH - M:
                continue
            if any(x < r[0] + r[2] + G and r[0] - G < x + RW and y < r[1] + r[3] + G and r[1] - G < y + H for r in rs):
                continue
            # lattice 8.64 from the slot grid
            over = [r for r in rs if x < r[0] + r[2] and r[0] < x + RW]
            if xf["orient"] == "R0":
                gap = min([r[1] - (y + H) for r in over if r[1] >= y + H] + [TH - M - (y + H)])
            else:
                gap = min([y - (r[1] + r[3]) for r in over if r[1] + r[3] <= y] + [y - M])
            best.append((abs(x + RW / 2 - cx) + abs(y + H / 2 - cy), x, y, gap))
    assert best, "no row site"
    good = [b for b in best if b[3] >= 34.56] or best
    return min(good)


def main():
    src, out, side_src, side_out = sys.argv[1:]
    P = json.loads(Path(src).read_text())
    Ps = S.Plan(S.load(src), src)
    T = json.loads(Path(side_src).read_text())
    plan_dir = Path("physical/die_plan/s81")
    doc = {m: json.loads((plan_dir / f"inputs/core_pins/{m}.json").read_text()) for _, m in ROW}
    ins = {m: json.loads(Path(f"{VIEW}/{m}/insertion.json").read_text()) for _, m in ROW}
    report = {}
    for tn, t in P["partition_types"].items():
        hc = t.get("hard_cores") or []
        old = next((c for c in hc if c.get("module") == "ot_s81dv_xfin"), None)
        if old is None:
            continue
        _, x0, y0, gap = site(t, old)
        idx = hc.index(old)
        ot = next(x for x in t["clock"]["taps"] if x["name"] == "u_c.u_xf.clk")
        rows, taps = [], []
        for i, (sub, m) in enumerate(ROW):
            c = dict(inst=f"u_c.u_xf.{sub}", module=m, lib=f"{VIEW}/{m}/{m}_tt.lib", lef=f"{VIEW}/{m}/{m}.lef", origin_um=[R(x0 + i * (W + G)), R(y0)],
                     outline_um=[W, H], orient=old["orient"], track_offset_um=[0.0, 0.0], pins_file=f"inputs/core_pins/{m}.json", obs_max="M5")
            pins = [(q["name"], q["layer"], q["x"], q["y"]) for q in doc[m]["pins"]]
            dx, dy = offset(Ps, tn, c, pins)
            assert dx is not None and dy is not None, (tn, sub, dx, dy)
            c["track_offset_um"] = [dx, dy]
            ck = next(q for q in doc[m]["pins"] if q["name"] == "clk")
            a = CK._orient_pt(c["orient"], W, H, ck["x"], ck["y"])
            taps.append(dict(ot, name=f"{c['inst']}.clk", xy=[R(c["origin_um"][0] + dx + a[0]), R(c["origin_um"][1] + dy + a[1])],
                             insertion_ps=ins[m]["tt"]["boundary"]["mean"], insertion_ff_ps=ins[m]["ff"]["boundary"]["mean"],
                             budget_owner=f"parent_budget pin_register_mean {VIEW}/{m}/insertion.json",
                             note="XFIN-DISSOLVE 11-04: early core tap at the boundary-register mean"))
            rows.append(c)
        hc[idx:idx + 1] = rows
        tt = t["clock"]["taps"]; i = tt.index(ot); tt[i:i + 1] = taps
        # grid taps the row now covers: to the nearest clear edge (delta_eg_taps form)
        boxes = placement_boxes(t, halo=S.TAP_CLEAR_UM); clear = S.TAP_CLEAR_UM; mv = []
        for a in t["clock"].get("added_taps", []):
            x, y = a["xy"]
            for bb in boxes.values():
                if bb[0] < x < bb[2] and bb[1] < y < bb[3]:
                    cs = sorted([(x - bb[0], R(bb[0] - .01), y), (bb[2] - x, R(bb[2] + .01), y), (y - bb[1], x, R(bb[1] - .01)), (bb[3] - y, x, R(bb[3] + .01))])
                    for _, nx, ny in cs:
                        if not any(b[0] < nx < b[2] and b[1] < ny < b[3] for b in boxes.values()) and not any(o is not a and abs(nx - o["xy"][0]) < clear and abs(ny - o["xy"][1]) < clear for o in t["clock"]["added_taps"]):
                            break
                    else:
                        raise SystemExit(("no tap site", tn, a))
                    mv.append((a["name"], [x, y], [nx, ny])); a["xy"] = [nx, ny]; break
        report[tn] = dict(orient=old["orient"], site=[x0, y0], pin_side_gap=R(gap), old=old["origin_um"], off=rows[0]["track_offset_um"], taps_moved=mv)
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    for tn in report:
        t = P["partition_types"][tn]
        lc = t["clock"].get("landing_contract") or {}
        st = T["collector"]["types"].get(tn) or {}
        tree = json.loads(json.dumps(RT.for_type(Pn, tn)))
        old = lc.get("collector_tree") or st.get("tree")
        report[tn].update(reset_depth=[old["depth"], tree["depth"]], relays=[len(old["relays"]), len(tree["relays"])])
        publish_tree(lc, st, tree, report[tn])
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    print(json.dumps(report, indent=0))


if __name__ == "__main__":
    main()
