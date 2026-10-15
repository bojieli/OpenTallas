#!/usr/bin/env python3
"""Cut analysis of the STATIC TP8 collective cluster qfd_io_collective_static (owner rule "cut analysis before RTL",
target <= 0.55, band 0.55-0.60), on the floorplan of tools/ref_tile/specs_qcollio/qfd_io_collective_s1.json.

Vertical cut lines (E-W flows) use the horizontal layers M4 (48 nm) + M6 (64 nm, minus 13.6 % PG pair/escape); horizontal
cut lines (N-S flows) use the vertical layers M5 (48 nm) + M3 (36 nm, minus 50 %: cell-pin access reserve).  A layer is
lost over the span of every block whose LEF OBS holds it: ot_coll_fold_slice M1-M6, both SRAM macros M1-M4.  M2 / M7
(PG) are left out.  Demand = bits of every flow whose two ends lie on opposite sides of the cut (each bus counted once).
Flows follow rtl/rom/ot_coll_tp8_static.sv (A: producer pins / P ring / up; B: pairing / pre-fold; C/W: S ring /
SerDes send; D: SerDes receive / cross fold; E: R ring / ur; F: dr / output).
usage: python3 tools/qwen_coll_static_cut.py [--spec SPEC.json]"""
import argparse
import json

TR_H = {"M4": 1 / 0.048, "M6": (1 / 0.064) * (1 - 0.136)}
TR_V = {"M5": 1 / 0.048, "M3": (1 / 0.036) * 0.5}
OBS = {"fold": {"M3", "M4", "M5", "M6"}, "sram": {"M3", "M4"}}
SIZE = {"ot_coll_fold_slice": (181.44, 181.44), "ot_sram_1r1w_512x128_m4_r2c2": (174.096, 29.7),
        "ot_sram_1r1w_32x546_m1": (177.768, 81.0)}


def blocks_of(spec):
    out = []
    for c in spec["children"] + spec["macros"]:
        m = c["view"].rstrip("/").split("/")[-1]
        w, h = SIZE[m]
        out.append((c["inst"], "fold" if "fold" in m else "sram", c["at"][0], c["at"][1], w, h))
    return out


def free_span(blocks, lay, pos, axis, L):
    """length along the cut line not covered by a block holding layer lay (axis 'x': vertical line at x=pos)."""
    cov = []
    for _, k, bx, by, w, h in blocks:
        if lay not in OBS[k]:
            continue
        if axis == "x" and bx <= pos <= bx + w:
            cov.append((by, by + h))
        if axis == "y" and by <= pos <= by + h:
            cov.append((bx, bx + w))
    cov.sort()
    free, cur = 0.0, 0.0
    for a, b in cov:
        if a > cur:
            free += a - cur
        cur = max(cur, b)
    return free + max(0.0, L - cur)


def flows(spec):
    """(name, bits, (x0, y0), (x1, y1)) from the spec geometry."""
    W, H = spec["outline"]["w"], spec["outline"]["h"]
    ch = {c["inst"]: c for c in spec["children"]}
    mac = [m for m in spec["macros"]]
    xa = ch["*g_xf?0?*u_fs"]["at"][0]
    xc = ch["*g_pf?0?*u_fs"]["at"][0]
    xs = [m for m in mac if "sring" in m["inst"]][0]["at"][0]
    xd = [m for m in mac if "pring" in m["inst"]][0]["at"][0]
    sl = 181.44
    ymid = H / 2
    pin = spec["pin_ranges"]

    def nx(p):
        return sum(pin[p]) / 2
    ain, aout = (xa, ymid), (xa + sl, ymid)                  # cross fold: src W face, sum E face (R0)
    cin, cout = (xc + sl, ymid), (xc, ymid)                  # pre fold MY: src E face, sum W face
    sring = (xs + 87.0, ymid)
    pring, rring = (xd + 89.0, 260.0), (xd + 89.0, 730.0)
    pair = ((xc + sl + xd) / 2, ymid)                         # pairing / gather hold registers between C and D
    pfq = ((xs + 174.1 + xc) / 2, ymid)                       # pf_q / sx copies / S ring write mux between S and C
    xrq = ((xa + sl + xs) / 2, ymid)                          # xr_q between A and S
    outq = (nx("out_data"), H - 40.0)                         # output registers under the out pins
    inq = (nx("in_data"), H - 40.0)
    E = lambda p: (W, sum(pin[p]) / 2)
    Wf = lambda p: (0.0, sum(pin[p]) / 2)
    return [
        ("in_* N pins -> producer regs", 548, (nx("in_data"), H), inq),
        ("producer regs -> P ring write", 546, inq, pring),
        ("producer regs -> up_rec (E)", 546, inq, E("up_rec")),
        ("cmd N pins -> slot sequencer (at producer regs)", 50, (nx("cmd_tag"), H), inq),
        ("dp_rec (E) -> pairing", 546, E("dp_rec"), pair),
        ("P ring read -> pairing", 546, pring, pair),
        ("pairing lo/hi -> pre-fold src (C E face)", 1024, pair, cin),
        ("gather hold word (g_d mux at pairing) -> S/sx mux", 512, pair, pfq),
        ("pre-fold sum (C W face) -> pf_q", 512, cout, pfq),
        ("pf_q -> S ring write", 640, pfq, sring),
        ("pf_q -> sx0_rec (E)", 546, pfq, E("sx0_rec")),
        ("pf_q -> sx1_rec (W)", 546, pfq, Wf("sx1_rec")),
        ("pf_q -> sx2_rec (W)", 546, pfq, Wf("sx2_rec")),
        ("S ring read -> cross-fold src (A W face)", 640, sring, ain),
        ("sr0_rec (E) -> cross-fold src", 546, E("sr0_rec"), ain),
        ("sr1_rec (W) -> cross-fold src", 546, Wf("sr1_rec"), ain),
        ("sr2_rec (W) -> cross-fold src", 546, Wf("sr2_rec"), ain),
        ("gather output select (at A src mux) -> out regs", 512, ain, outq),
        ("cross-fold sum (A E face) -> xr_q", 512, aout, xrq),
        ("xr_q -> ur_rec (E)", 514, xrq, E("ur_rec")),
        ("xr_q -> R ring write", 546, xrq, rring),
        ("R ring read -> out regs", 514, rring, outq),
        ("dr_rec (E) -> out regs", 514, E("dr_rec"), outq),
        ("out regs -> out_* N pins", 517, outq, (nx("out_data"), H)),
        ("tokens / tags / control", 120, pair, xrq),
    ]


def analyse(spec):
    W, H = spec["outline"]["w"], spec["outline"]["h"]
    bl = blocks_of(spec)
    fl = flows(spec)
    rows = []
    xs = sorted({round(b[2], 2) for b in bl} | {round(b[2] + b[4], 2) for b in bl})
    cuts_x = sorted(set([x + 0.5 * (y - x) for x, y in zip(xs, xs[1:])] + [b[2] + b[4] / 2 for b in bl]))
    for x in cuts_x:
        d = sum(b for _, b, p, q in fl if min(p[0], q[0]) < x < max(p[0], q[0]))
        cap = sum(free_span(bl, lay, x, "x", H) * t for lay, t in TR_H.items())
        rows.append(("vertical", x, d, cap, d / cap if cap else 99.0))
    ys = sorted({round(b[3], 2) for b in bl} | {round(b[3] + b[5], 2) for b in bl})
    cuts_y = sorted(set([y0 + 0.5 * (y1 - y0) for y0, y1 in zip(ys, ys[1:])] + [b[3] + b[5] / 2 for b in bl]))
    for y in cuts_y:
        d = sum(b for _, b, p, q in fl if min(p[1], q[1]) < y < max(p[1], q[1]))
        cap = sum(free_span(bl, lay, y, "y", W) * t for lay, t in TR_V.items())
        rows.append(("horizontal", y, d, cap, d / cap if cap else 99.0))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="tools/ref_tile/specs_qcollio/qfd_io_collective_s1.json")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    s = json.load(open(a.spec))
    W, H = s["outline"]["w"], s["outline"]["h"]
    rows = analyse(s)
    print(f"== {s['name']} {W} x {H} um")
    worst = max(rows, key=lambda r: r[4])
    for kind, pos, d, cap, u in rows:
        print(f"  {kind:<10} @ {pos:7.1f}  demand {d:5d}  tracks {cap:7.0f}  util {u:.2f}")
    verdict = "PASS" if worst[4] <= 0.55 else ("BAND" if worst[4] <= 0.60 else "FAIL")
    print(f"  worst cut {worst[0]} @ {worst[1]:.1f}: util {worst[4]:.2f} -> {verdict} (target <= 0.55, band <= 0.60)")
    if a.json:
        json.dump(dict(spec=a.spec, outline=[W, H], worst=dict(kind=worst[0], pos=worst[1], demand=worst[2],
                       tracks=round(worst[3]), util=round(worst[4], 3)), verdict=verdict,
                       cuts=[dict(kind=k, pos=round(p, 2), demand=d, tracks=round(c), util=round(u, 3))
                             for k, p, d, c, u in rows]), open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
