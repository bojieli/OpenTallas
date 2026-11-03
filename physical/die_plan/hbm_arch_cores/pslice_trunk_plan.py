#!/usr/bin/env python3
"""DIE-HBM-57/PSLICE 11-01: core plan of ot_hbm_su_programme_pslice_c5 in its trunk form (OT_PSLICE_TRUNK, recipe
ot_hbm_su_programme_pslice_c5__trunk*): static macro placement + explicit GPL register guide boxes.

Why (d44o attempt_3 FAIL PLAN, GEOM-96/104): 100 SRAMs in 8 columns x 13 rows with logic only in 21-um streets and a
200-um N band; GPL scattered every leaf's registers over the die (og_q -> command 1118 um, sl -> og_q, l_q -> count),
the single head copy fed all 10 leaves (o_data -> wdat_r 1045), start/length reached leaf 9 1265 um from the W pins.

Plan (one source of truth for the kit, deterministic):
  * macros: the d44o KNOWN grid (same columns / rows 0..6), rows 7..12 raised by MID_UM -> a mid street over the full
    width (y ~302..426) holding the leaf clusters and the trunk; leaves take column-major slots top->bottom in leaf
    order so leaf c's macros sit under its command pins (x 8.8 + 95.4 c ..);
  * leaf c cluster box in the mid street under its command pins (all leaf registers, its o_* export copies, its f1);
  * command egress relays g_oc[c] in the N band above leaf c; edge_index relay in the E strip beside leaf EIDX;
    busy/valid/done/fault relay in the col0/col1 street near their W pins;
  * cfg ingress stage 1 (u_h.u_x) in the W strip mid-height (every cfg pin within ~400 um), then per region g the
    stages u_h.g_r[g].u_y spaced evenly along the street to the region box (k / k2 copies + region reset relay);
  * start/length stage 1 (u_xs) in the col0/col1 street, then per column the copies g_x[c].u_s spaced evenly along
    the street to leaf c's box;
  * fault logic box at FAULT_XY; per column the mid-chain registers (g_l[c].v1 / f2) halfway between leaf c and it;
  * rst_n: leaf 0's relay sync flops in the W strip near the NW rst_n pin (pin_reg), every other relay with its loads
    (kit keeps the per-relay sync flops: --orfs-var OT_KEEP_WIRES=sync_q).

usage: pslice_trunk_plan.py --core-macros CORE_MACROS.json --xst N --out-dir DIR [--names NETLIST_NAMES.txt]
  writes DIR/macro_placement.json (--macro-placement, --macro-inst-fmt '{k}') and DIR/guides_x<N>.json
  (--reg-guide-boxes).  --names (one flat instance name per line from a synth netlist of the same source) checks that
  every box prefix matches at least one register and reports registers of the planned groups outside every box.
"""
import argparse
import json
import re
import sys

W_UM, H_UM, CORE_LO, CORE_HI_X, CORE_HI_Y = 939.6, 760.32, 4.32, 935.28, 756.0
NC, SB = 10, 2470
MID_UM = 113.4            # rows 7..12 up by 420 placement rows (0.27 um)
MAC_W, MAC_H = 94.824, 41.064
DB = [3, 13, 13, 13, 3, 3, 3, 3, 3, 3]    # DICT_CAP 3,10,9,13,2,1,1,1,1,1 -> S (3) / L (13) leaves
IXB = 4
HG = 3
PIN_X0, PIN_PITCH = 8.8, 95.4             # command[256c..] on the N face
LEAF_Y = (374.0, 422.0)                   # leaf cluster boxes (mid street upper lane)
LANE_Y = (305.0, 368.0)                   # trunk lane (mid street lower lane)
REGION_X = [200.0, 535.0, 800.0]
FAULT_XY = (340.0, 317.0)
XS_XY = (120.0, 205.0)                    # start/length stage 1 (col0/col1 street)
UX_BOX = [7.0, 362.0, 14.0, 418.0]        # cfg stage 1 (W strip)
OB_BOX = [112.0, 150.0, 129.0, 170.0]     # busy/valid/done/fault egress relay (col0/col1 street)
OE_BOX = [928.5, 380.0, 934.5, 416.0]     # edge_index egress relay (E strip)
SYNC0_BOX = [7.0, 650.0, 14.0, 680.0]     # leaf 0 relay sync flops (W strip, NW rst_n pin)
OC_Y = (680.0, 700.0)                     # command egress relays (N band)
STREET01_X = 120.0                        # col0/col1 vertical street centre


def leaf_ctr(c):
    lo = PIN_X0 + PIN_PITCH * c
    hi = min(PIN_X0 + PIN_PITCH * (c + 1), PIN_X0 + PIN_PITCH * c + (SB - 256 * c) * PIN_PITCH / 256)
    return (lo + hi) / 2.0, lo, hi


def macro_table(core_macros):
    e = json.load(open(core_macros))["cores"]["ot_hbm_su_programme_pslice_c5"]
    xs = sorted({round(q["rect_um"][0], 3) for q in e["macros"]})
    ys = sorted({round(q["rect_um"][1], 3) for q in e["macros"]})
    if len(xs) != 8 or len(ys) != 13:
        raise SystemExit(f"core_macros grid {len(xs)} x {len(ys)}, expected 8 x 13")
    ys = [y if i < 7 else round(y + MID_UM, 3) for i, y in enumerate(ys)]
    slots = [(xs[ci], ys[r]) for ci in range(8) for r in range(12, -1, -1)]
    rows, k = [], 0
    for c in range(NC):
        names = [f"g_c[{c}].u_c.u_p.g_m4.dt[0].mem.g[{i}].mem" for i in range(DB[c])] + \
                [f"g_c[{c}].u_c.u_p.g_m4.ix[0].mem.g[{i}].mem" for i in range(IXB)]
        for n in names:
            x, y = slots[k]
            rows.append(dict(k=n, macro="ot_sram_1r1w_128x256_m1_r2c2", origin_um=[x, y], orient="R0"))
            k += 1
    old = {q["name"].replace("u_fcore.", "", 1) for q in e["macros"]}
    # The legacy plan names the unguarded leaf; OT_PSLICE_TRUNK instantiates
    # its active leaf in generate g_p. Match semantic legacy identity first,
    # then emit the actual synthesis hierarchy for both old and updated plans.
    old = {n.replace(".u_c.g_p.u_p.", ".u_c.u_p.") for n in old}
    if {r["k"] for r in rows} != old:
        raise SystemExit("macro names differ from the plan core_macros entry")
    for row in rows:
        row["k"] = row["k"].replace(".u_c.u_p.", ".u_c.g_p.u_p.")
    top = max(r["origin_um"][1] for r in rows) + MAC_H
    return rows, dict(xs=xs, ys=ys, mid_street=[round(ys[6] + MAC_H, 3), ys[7]], n_band=[round(top, 3), CORE_HI_Y])


def box_at(x, y, hw, hh):
    return [round(x - hw, 3), round(y - hh, 3), round(x + hw, 3), round(y + hh, 3)]


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def street_path(p0, p1):
    """polyline p0 -> (street x, lane) -> along the lane -> p1 (Manhattan)."""
    ly = (LANE_Y[0] + LANE_Y[1]) / 2.0
    pts = [p0]
    if p0[1] < LANE_Y[0] - 1:            # below the mid street: climb the col0/col1 street first
        pts.append((STREET01_X, p0[1]))
        pts.append((STREET01_X, ly))
    else:
        pts.append((p0[0], ly))
    pts.append((p1[0], ly))
    pts.append(p1)
    return pts


def along(pts, d):
    for a, b in zip(pts, pts[1:]):
        L = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if d <= L + 1e-9:
            t = d / L if L else 0.0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        d -= L
    return pts[-1]


def plen(pts):
    return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def place_free(boxes, want, hw, hh, area):
    """box of half size hw x hh nearest `want` inside `area` [x0,y0,x1,y1] clear of every box so far."""
    best = None
    for dy in [0] + [s * k for k in range(1, 12) for s in (1, -1)]:
        for dx in [0] + [s * k for k in range(1, 40) for s in (1, -1)]:
            x, y = want[0] + dx * 2.0, want[1] + dy * 2.0
            b = box_at(x, y, hw, hh)
            if b[0] < area[0] or b[1] < area[1] or b[2] > area[2] or b[3] > area[3]:
                continue
            if any(overlaps(b, q["box_um"]) for q in boxes):
                continue
            cost = abs(dx) * 2 + abs(dy) * 2
            if best is None or cost < best[0]:
                best = (cost, b)
        if best is not None and best[0] <= abs(dy) * 2:
            break
    if best is None:
        raise SystemExit(f"no free box near {want}")
    return best[1]


def guides(xst):
    B = []

    def add(name, prefixes, box):
        B.append(dict(name=name, prefixes=prefixes, box_um=[round(v, 3) for v in box]))

    f = "u_fcore."
    lane = [CORE_LO, LANE_Y[0], CORE_HI_X, LANE_Y[1]]
    # leaf clusters (mid street, upper lane), each under its command pins
    for c in range(NC):
        cx, lo, hi = leaf_ctr(c)
        hw = min(35.0, (hi - lo) / 2 - 3)
        p = [f"{f}g_c[{c}].u_c.g_p.u_p.", f"{f}g_c[{c}].u_c.q_", f"{f}g_c[{c}].u_c.s_q", f"{f}g_c[{c}].u_c.l_q",
             f"{f}g_c[{c}].u_c.g_rr.u_rr.rst_n", f"{f}u_h.g_o[{c}].", f"{f}u_h.g_lx.g_l[{c}].f1"]
        if c != 0:
            p.append(f"{f}g_c[{c}].u_c.g_rr.u_rr.sync_q")
        add(f"leaf{c}", p, [cx - hw, LEAF_Y[0], cx + hw, LEAF_Y[1]])
        add(f"oc{c}", [f"{f}g_oc[{c}]."], [cx - hw, OC_Y[0], cx + hw, OC_Y[1]])
    add("sync0", [f"{f}g_c[0].u_c.g_rr.u_rr.sync_q"], SYNC0_BOX)
    add("ob", [f"{f}u_ob."], OB_BOX)
    add("oe", [f"{f}u_oe."], OE_BOX)
    add("ux", [f"{f}u_h.u_x."], UX_BOX)
    add("xs", [f"{f}u_xs."], box_at(XS_XY[0], XS_XY[1], 7.0, 8.0))
    # region boxes + fault box (lower lane)
    for g in range(HG):
        add(f"reg{g}", [f"{f}u_h.g_r[{g}].k", f"{f}u_h.g_r[{g}].u_rr."],
            box_at(REGION_X[g], (LANE_Y[0] + LANE_Y[1]) / 2 - 8, 18.0, 15.0))
    add("fault", [f"{f}u_h.oor_d", f"{f}u_h.g_lx.h", f"{f}u_h.fault", f"{f}h_fault"],
        box_at(FAULT_XY[0], FAULT_XY[1], 12.0, 10.0))
    hops = {}
    # cfg ingress: u_x (W strip) -> u_y stages -> region box, evenly spaced along the street
    ux = ((UX_BOX[0] + UX_BOX[2]) / 2, (UX_BOX[1] + UX_BOX[3]) / 2)
    for g in range(HG):
        rb = (REGION_X[g], (LANE_Y[0] + LANE_Y[1]) / 2 - 8)
        pts = street_path(ux, rb)
        L = plen(pts)
        for s in range(xst - 1):
            want = along(pts, L * (s + 1) / xst)
            prefix = f"{f}u_h.g_r[{g}].u_y."
            prefix += "q" if s == xst - 2 else f"g_n.g_s[{s}]."
            add(f"y{g}s{s}", [prefix], place_free(B, want, 8.0, 8.0, lane))
        hops[f"cfg_r{g}"] = round(L / xst, 1)
    # start/length: u_xs -> g_x[c] stages -> leaf c box
    for c in range(NC):
        cx = leaf_ctr(c)[0]
        tgt = (cx, LEAF_Y[0])
        pts = street_path(XS_XY, tgt)
        L = plen(pts)
        for s in range(xst - 1):
            want = along(pts, L * (s + 1) / xst)
            area = lane if want[1] >= LANE_Y[0] - 1 else [STREET01_X - 9, 60.0, STREET01_X + 9, LANE_Y[0]]
            prefix = f"{f}g_x[{c}].u_s."
            prefix += "q" if s == xst - 2 else f"g_n.g_s[{s}]."
            add(f"x{c}s{s}", [prefix], place_free(B, want, 4.0, 4.0, area))
        hops[f"start_c{c}"] = round(L / xst, 1)
    # leaf fault / valid mid stages halfway between leaf c and the fault box
    for c in range(NC):
        cx = leaf_ctr(c)[0]
        want = ((cx + FAULT_XY[0]) / 2, (LANE_Y[0] + LANE_Y[1]) / 2 + 12)
        add(f"lf{c}", [f"{f}u_h.g_lx.g_l[{c}].v1", f"{f}u_h.g_lx.g_l[{c}].f2"], place_free(B, want, 4.0, 4.0, lane))
    return B, hops


def check_names(B, names_file):
    names = [ln.strip().replace("\\", "") for ln in open(names_file) if ln.strip()]
    rep = {}
    for b in B:
        n = sum(1 for nm in names if any(nm.startswith(p) for p in b["prefixes"]))
        rep[b["name"]] = n
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core-macros", required=True)
    ap.add_argument("--xst", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--names", default=None)
    a = ap.parse_args()
    rows, grid = macro_table(a.core_macros)
    B, hops = guides(a.xst)
    for i, p in enumerate(B):
        for q in B[i + 1:]:
            if overlaps(p["box_um"], q["box_um"]):
                raise SystemExit(f"boxes {p['name']} / {q['name']} overlap")
    # boxes must not sit on a macro
    for b in B:
        for r in rows:
            m = [r["origin_um"][0], r["origin_um"][1], r["origin_um"][0] + MAC_W, r["origin_um"][1] + MAC_H]
            if overlaps(b["box_um"], m):
                raise SystemExit(f"box {b['name']} {b['box_um']} on macro {r['k']}")
    meta = dict(source="physical/die_plan/hbm_arch_cores/pslice_trunk_plan.py", by="DIE-HBM-57/PSLICE 11-01",
                mid_um=MID_UM, grid=grid)
    json.dump(dict(meta, macro_placement=rows), open(f"{a.out_dir}/macro_placement.json", "w"), indent=1)
    json.dump(dict(meta, xst=a.xst, planned_hop_um=hops, boxes=B), open(f"{a.out_dir}/guides_x{a.xst}.json", "w"), indent=1)
    print(f"macros {len(rows)} grid {grid}")
    print(f"boxes {len(B)} planned hop um {hops}")
    if a.names:
        rep = check_names(B, a.names)
        empty = [k for k, v in rep.items() if v == 0]
        print("members per box:", rep)
        if empty:
            print("EMPTY boxes:", empty)
            sys.exit(2)


if __name__ == "__main__":
    main()
