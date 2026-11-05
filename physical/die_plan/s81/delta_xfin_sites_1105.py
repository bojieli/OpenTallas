#!/usr/bin/env python3
"""S81 XFIN-DISSOLVE site fix (DIE-S81-56 11-05): the 941 um core row of six C types sat on feedthrough stations (plan-time GEOM
ft-site read, advisory).  Each row moves to the nearest 8.64-lattice site with no station cell on a core, >= 8.64 um clear of the other
cores, pin side room 34.56 um when any such site exists.  Slots, stations, core order and orient stay.
    python3 delta_xfin_sites_1105.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT     (cwd = repo root)
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import check as CK, schema as S, reset_tree as RT, gen_phys
from plan_event_1104 import plan_text, publish_tree
from placement_obstacles import placement_boxes
from ft_full_stage import load
from die_hop_scan import input_site, normal_slot
from delta_xfin_split_1104 import offset, W, H, G, M, RW, R
TYPES = ["dsdv_slice_c1x_C__t1", "dsdv_slice_c1x_C__t10", "dsdv_slice_c1x_C__t3", "dsdv_slice_c1x_C__t4", "dsdv_slice_c1x_C__t8",
         "dsdv_slice_lepe_nh_mus_C__t1"]
EPS = 1e-3


def stations(Ps, tn, t):
    """Same cells and centres as check.check_ft_macro_sites."""
    full = load(Ps, tn); out = []; pins = {}
    for bus, bit, _l, x, y, face in gen_phys.type_pins(Ps, tn):
        pins.setdefault(bus, {})[bit] = (x, y, face)
    for slot in t.get("ft_slots") or []:
        name = slot["name"]; stages = int(slot.get("stations", 1))
        if name in full:
            for row in full[name].values():
                x, y = row["xy"]; w, h = row["size"]; out.append((x, y, x + w, y + h))
            continue
        pi, po = pins.get(name + "_i", {}), pins.get(name + "_o", {})
        normal = normal_slot(Ps, tn, name, full=full)
        for bit in sorted(set(pi) | set(po)):
            ap = pi.get(bit) or po[bit]; bp = po.get(bit) or pi[bit]
            a, b = input_site(ap), input_site(bp); route = CK.zroute(a, b, ap[2], bp[2]); L = CK.plen(route)
            for j in range(stages):
                if slot.get("bit_sites_um") and j > 0:
                    x, y = slot["bit_sites_um"][j - 1][bit]; w, h = slot["bit_site_cell_um"]; out.append((x, y, x + w, y + h))
                else:
                    xy = a if (j == 0 and normal) or slot.get("bit_sites_um") else tuple(slot["regs_um"][j]) if slot.get("regs_um") else CK.point_at(route, L * j / stages)
                    out.append((xy[0], xy[1], xy[0], xy[1]))
    return out


def new_site(t, row, st):
    x0, y0 = row[0]["origin_um"]
    rs = [c["origin_um"] + c["outline_um"] for c in t["hard_cores"] if c not in row]
    TW, TH = t["outline_um"]; sites = []
    for iy in range(int((TH - 2 * M - H) / 8.64) + 1):
        y = M + iy * 8.64
        for ix in range(int((TW - 2 * M - RW) / 8.64) + 1):
            x = M + ix * 8.64
            if any(x < r[0] + r[2] + G and r[0] - G < x + RW and y < r[1] + r[3] + G and r[1] - G < y + H for r in rs):
                continue
            if any(min(s[2], x + i * (W + G) + W) - max(s[0], x + i * (W + G)) > -EPS and min(s[3], y + H) - max(s[1], y) > -EPS for i in range(5) for s in st):
                continue
            over = [r for r in rs if x < r[0] + r[2] and r[0] < x + RW]
            if row[0]["orient"] == "R0":
                gap = min([r[1] - (y + H) for r in over if r[1] >= y + H] + [TH - M - (y + H)])
            else:
                gap = min([y - (r[1] + r[3]) for r in over if r[1] + r[3] <= y] + [y - M])
            sites.append((abs(x - x0) + abs(y - y0), R(x), R(y), R(gap)))
    good = [s for s in sites if s[3] >= 34.56] or sites
    assert good, "no clean row site"
    return min(good)


def main():
    src, out, side_src, side_out = sys.argv[1:]
    P = json.loads(Path(src).read_text()); Ps = S.Plan(S.load(src), src)
    T = json.loads(Path(side_src).read_text()); doc = {}; report = {}
    for tn in TYPES:
        t = P["partition_types"][tn]
        row = [c for c in t["hard_cores"] if c["inst"].startswith("u_c.u_xf.")]
        assert len(row) == 5
        _, x, y, gap = new_site(t, row, stations(Ps, tn, Ps.types[tn]))
        for i, c in enumerate(row):
            m = c["module"]
            d = doc.setdefault(m, json.loads(Path(f"physical/die_plan/s81/inputs/core_pins/{m}.json").read_text()))
            c["origin_um"] = [R(x + i * (W + G)), y]; c["track_offset_um"] = [0.0, 0.0]
            dx, dy = offset(Ps, tn, c, [(q["name"], q["layer"], q["x"], q["y"]) for q in d["pins"]])
            assert dx is not None and dy is not None, (tn, c["inst"])
            c["track_offset_um"] = [dx, dy]
            ck = next(q for q in d["pins"] if q["name"] == "clk")
            a = CK._orient_pt(c["orient"], W, H, ck["x"], ck["y"])
            tap = next(q for q in t["clock"]["taps"] if q["name"] == f"{c['inst']}.clk")
            tap["xy"] = [R(c["origin_um"][0] + dx + a[0]), R(c["origin_um"][1] + dy + a[1])]
        boxes = placement_boxes(t, halo=S.TAP_CLEAR_UM); mv = []
        for a in t["clock"].get("added_taps", []):
            ax, ay = a["xy"]
            for bb in boxes.values():
                if bb[0] < ax < bb[2] and bb[1] < ay < bb[3]:
                    cs = sorted([(ax - bb[0], R(bb[0] - .01), ay), (bb[2] - ax, R(bb[2] + .01), ay), (ay - bb[1], ax, R(bb[1] - .01)), (bb[3] - ay, ax, R(bb[3] + .01))])
                    for _, nx, ny in cs:
                        if not any(b[0] < nx < b[2] and b[1] < ny < b[3] for b in boxes.values()) and not any(o is not a and abs(nx - o["xy"][0]) < S.TAP_CLEAR_UM and abs(ny - o["xy"][1]) < S.TAP_CLEAR_UM for o in t["clock"]["added_taps"]):
                            break
                    else:
                        raise SystemExit(("no tap site", tn, a))
                    mv.append(a["name"]); a["xy"] = [nx, ny]; break
        report[tn] = dict(site=[x, y], pin_side_gap=gap, taps_moved=len(mv))
    Path(out).write_text(plan_text(P)); Pn = S.Plan(S.load(out), out)
    for tn in TYPES:
        t = P["partition_types"][tn]; lc = t["clock"].get("landing_contract") or {}; st = T["collector"]["types"].get(tn) or {}
        old = lc.get("collector_tree") or st.get("tree")
        tree = json.loads(json.dumps(RT.for_type(Pn, tn)))
        report[tn].update(reset_depth=[old["depth"], tree["depth"]], relays=[len(old["relays"]), len(tree["relays"])])
        publish_tree(lc, st, tree, report[tn])
    Path(side_out).write_text(json.dumps(T, separators=(",", ":"))); Path(out).write_text(plan_text(P))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
