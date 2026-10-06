#!/usr/bin/env python3
"""Floorplan of the bank-built HBM attention die tile hfd_attn_tile_b (rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv):
four option-B quads (left MY, right R0, input edges facing the central channel, pins on the tile track grid) and every
pipeline bank placed along its route.  Each pipe is a polyline from its source (pin / bank) to its sink; its N stages
are spread evenly along it and every bank snaps to the nearest free SN / EW slot in the channels.  Prints every hop
length (Manhattan, bank centre to bank centre, + the source / sink pins) and refuses a hop above --max-hop.

    python3 tools/hbm_attn_die_tile_place.py --out physical/hbm_attn_tile_r/die_tile/macro_placement_b.tcl \
        --report physical/hbm_attn_tile_r/die_tile/floorplan_b.json [--NK 4 ...]
"""
import argparse
import json
import math

TW, TH = 1349.112, 1349.976
# the core snaps to the site / row grid (0.054 / 0.27 um): banks at the east / north edges sit inside it
CW_, CH_ = int(TW / 0.054) * 0.054, int(TH / 0.27) * 0.27
QW, QH = 514.89, 562.95
SNW, SNH = 105.84, 11.88           # ot_attn_bank_sn544
EWW, EWH = 11.88, 105.84           # ot_attn_bank_ew544
HALO = 5.0
QL_X, QR_X = 43.230, 788.4         # MY / R0 origins on the quads' M4 / M5 pin phase (x 30 / 0 nm mod 48)
QY = (49.968, 736.8)               # quad rows (y 0 nm mod 48)
PITCH = 0.192


def quads():
    return {(y, x): ((QL_X if x == 0 else QR_X), QY[y], "MY" if x == 0 else "R0") for y in (0, 1) for x in (0, 1)}


def qbox(y, x):
    x0, y0, _ = quads()[(y, x)]
    return (x0 - HALO, y0 - HALO, x0 + QW + HALO, y0 + QH + HALO)


def overlap(a, b, gap=0.0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


class Plan:
    def __init__(self):
        self.boxes = [qbox(y, x) for y in (0, 1) for x in (0, 1)]
        self.banks = []                                     # (name, orient, x, y, w, h)

    def free(self, box):
        if box[0] < 0 or box[1] < 0 or box[2] > TW or box[3] > TH:
            return False
        return not any(overlap(box, b, 1.5) for b in self.boxes)

    def put(self, name, orient, x, y, w, h):
        box = (x, y, x + w, y + h)
        if not self.free(box):
            raise SystemExit(f"{name}: ({x:.3f}, {y:.3f}) {w} x {h} overlaps")
        self.boxes.append(box)
        self.banks.append((name, orient, round(x, 3), round(y, 3), w, h))
        return (x + w / 2, y + h / 2)

    def snap(self, name, cx, cy, orient="R0", ew=False):
        """the free SN (or EW) slot nearest the ideal centre (cx, cy): a spiral over a 2.16 um grid"""
        w, h = (EWW, EWH) if ew else (SNW, SNH)
        best = None
        for r in range(0, 400):
            for dx in range(-r, r + 1):
                for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    x = round((cx - w / 2 + dx * 2.16) / 0.054) * 0.054
                    y = round((cy - h / 2 + dy * 2.16) / 0.27) * 0.27
                    if self.free((x, y, x + w, y + h)):
                        d = abs(x + w / 2 - cx) + abs(y + h / 2 - cy)
                        if best is None or d < best[0]:
                            best = (d, x, y)
            if best is not None and r > 3:
                break
        if best is None:
            raise SystemExit(f"{name}: no free slot near ({cx:.1f}, {cy:.1f})")
        return self.put(name, orient, best[1], best[2], w, h)


def bname(pipe, s, c, ew):
    return f"{pipe}.gn.g_s\\[{s}\\].g_c\\[{c}\\].{'g_ew' if ew else 'g_sn'}.u_b"


def along(pts, t):
    """the point at fraction t of the polyline's Manhattan length"""
    seg = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    L = sum(seg) * t
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if L <= s or s == 0:
            f = 0 if s == 0 else L / s
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        L -= s
    return pts[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--max-hop", type=float, default=350.0)
    for k, v in dict(NK=4, NC=2, NR=3, PMID=1, NFC=2, NFR=3, NL=6, NI=4).items():
        ap.add_argument(f"--{k}", type=int, default=v)
    a = ap.parse_args()
    P = Plan()
    hops = []
    cc_x = (QL_X + QW + QR_X) / 2                         # central channel centre
    mc_y = (QY[0] + QH + QY[1]) / 2                       # middle channel centre
    # ---- pin banks: exact pin alignment (bank x0 = first pin - 0.396) where the chunks do not collide
    pin = {}

    def pins_s(pipe, first_x, nb, y, orient, row_step=0.0):
        cs = []
        for c in range(nb):
            x = first_x + c * 544 * PITCH - 0.396
            if c and x < cs[-1][0] + SNW + 1.5:
                x = cs[-1][0] + SNW + 1.62                  # a jog of a few um, next chunk
            cs.append((x, y))
        return [P.put(bname(pipe, (0 if orient == "R0" else -1), c, False), orient, x, yy, SNW, SNH) for c, (x, yy) in enumerate(cs)]

    def pins_e(pipe, s, first_y, nb, x, orient):
        cs = []
        for c in range(nb):
            y = first_y + c * 544 * PITCH - 0.396
            if c and y < cs[-1] + EWH + 1.5:
                y = cs[-1] + EWH + 1.62
            cs.append(y)
        return [P.put(bname(pipe, s, c, True), orient, x, y, EWW, EWH) for c, y in enumerate(cs)]

    # inputs (stage 0 = the pin bank); outputs (last stage = the pin bank)
    pin["k"] = pins_s("u_pk", 0.624, 2, 0.0, "R0")
    pin["ci"] = pins_s("u_pc", 519.228, 3, 0.0, "R0")
    pin["cf"] = [P.put(bname("u_fc", a.NFC, c, False), "R0", x, round(CH_ - SNH, 3), SNW, SNH)
                 for c, x in enumerate([519.228 - 0.396, 519.228 - 0.396 + SNW + 1.62, 519.228 - 0.396 + 2 * (SNW + 1.62)])]
    pin["q"] = pins_e("u_pq", 0, 1236.864, 1, round(CW_ - EWW, 3), "MY")
    pin["ri"] = pins_e("u_pr", 0, 725.952, 3, round(CW_ - EWW, 3), "MY")
    pin["rf"] = pins_e("u_fr", a.NFR, 725.952, 3, 0.0, "MY")
    # i / o (pins y 624.2 .. 725.6) sit just below rf / ri: their banks end 1.62 um under the rf / ri banks (a ~6 um jog)
    yio = 725.952 - 0.396 - 1.62 - EWH
    pin["i"] = [P.put(bname("u_pi", 0, 0, True), "R0", 0.0, yio, EWW, EWH)]
    pin["o"] = [P.put(bname("u_oo", 0, 0, True), "R0", round(CW_ - EWW, 3), yio, EWW, EWH)]
    # ROOT at the channels' crossing
    root = [P.snap(bname("u_root", 0, c, False), cc_x, mc_y + (c - 1) * 14.0) for c in range(3)]
    rc = (sum(p[0] for p in root) / 3, sum(p[1] for p in root) / 3)

    def pipe(pipe_name, src_pts, n_mid, nb, first_stage, path, sink, tag):
        """n_mid banks (stages first_stage .. first_stage + n_mid - 1) between the source centre and the sink"""
        src = (sum(p[0] for p in src_pts) / len(src_pts), sum(p[1] for p in src_pts) / len(src_pts))
        pts = [src] + path + [sink]
        prev = src
        for k in range(n_mid):
            t = (k + 1) / (n_mid + 1)
            cx, cy = along(pts, t)
            cs = [P.snap(bname(pipe_name, first_stage + k, c, False), cx, cy + (c - (nb - 1) / 2) * 14.0) for c in range(nb)]
            cen = (sum(p[0] for p in cs) / nb, sum(p[1] for p in cs) / nb)
            hops.append((f"{tag} {k}", round(abs(cen[0] - prev[0]) + abs(cen[1] - prev[1]), 1)))
            prev = cen
        hops.append((f"{tag} ->", round(abs(sink[0] - prev[0]) + abs(sink[1] - prev[1]), 1)))

    cx = cc_x
    pipe("u_pk", pin["k"], a.NK, 2, 1, [(cx, 25.0)], rc, "k")
    pipe("u_pq", pin["q"], a.NK, 1, 1, [(cx, TH - 25.0)], rc, "q")
    pipe("u_pc", pin["ci"], a.NC, 3, 1, [(cx, 25.0)], rc, "ci")
    pipe("u_pr", pin["ri"], a.NR, 3, 1, [(TW - 30.0, mc_y), (cx, mc_y)], rc, "ri")
    cfc = (sum(p[0] for p in pin["cf"]) / 3, sum(p[1] for p in pin["cf"]) / 3)
    pipe("u_fc", root, a.NFC, 3, 0, [(cx, TH - 30.0)], cfc, "cf")
    rfc = (sum(p[0] for p in pin["rf"]) / 3, sum(p[1] for p in pin["rf"]) / 3)
    pipe("u_fr", root, a.NFR, 3, 0, [(cx, mc_y), (30.0, mc_y)], rfc, "rf")
    # ROOT -> PMID (a copy per quad row) -> ROW (a bank set per quad, beside its input pins)
    for y in (0, 1):
        q_in_y = QY[y] + (203 + 360) / 2
        mid = []
        for k in range(a.PMID):
            t = (k + 1) / (a.PMID + 1)
            my = rc[1] + (q_in_y - rc[1]) * t
            mid = [P.snap(bname(f"g_y\\[{y}\\].u_mid", k, c, False), cx, my + (c - 1) * 14.0) for c in range(3)]
            hops.append((f"mid{y} {k}", round(abs(my - rc[1]) / (a.PMID + 1), 1)))
        for x in (0, 1):
            qx = QL_X + QW if x == 0 else QR_X
            row = [P.snap(bname(f"g_y\\[{y}\\].g_x\\[{x}\\].u_row", 0, c, False),
                          qx + (SNW / 2 + 6 if x == 0 else -SNW / 2 - 6), q_in_y + (c - 1) * 14.0) for c in range(3)]
            mc = (sum(p[0] for p in mid) / 3, sum(p[1] for p in mid) / 3) if mid else rc
            rcn = (sum(p[0] for p in row) / 3, sum(p[1] for p in row) / 3)
            hops.append((f"row{y}{x}", round(abs(rcn[0] - mc[0]) + abs(rcn[1] - mc[1]), 1)))
            hops.append((f"row{y}{x} -> quad", round(abs(rcn[0] - qx) + 0, 1)))
    # results: each quad's 136 bits leave its outer edge at the register strip (option-B quad io: outputs on the
    # right / outer edge, local y 256 .. 307) -> an EW bank in the side channel beside them -> NL - 1 SN banks along
    # the side channel and the middle channel -> the merge at o (E edge)
    oc = pin["o"][0]
    for y in (0, 1):
        sy = QY[y] + 281.5
        y1 = (sy + mc_y) / 2                                # the second side-channel stage, half way to the middle
        for x in (0, 1):
            nm = f"g_y\\[{y}\\].g_x\\[{x}\\].u_res"
            if x == 0:
                xs, o, qe = 15.0, "MY", QL_X
            else:
                xs, o, qe = 1314.0, "R0", QR_X + QW
            e0 = P.put(bname(nm, 0, 0, True), o, xs, sy - EWH / 2, EWW, EWH)
            e1 = P.put(bname(nm, 1, 0, True), o, xs, y1 - EWH / 2, EWW, EWH)
            hops.append((f"res{y}{x} quad->bank", round(abs(qe - (xs + EWW / 2)), 1)))
            hops.append((f"res{y}{x} 0->1", round(abs(e1[1] - e0[1]), 1)))
            pipe(nm, [e1], a.NL - 2, 1, 2, [(xs + EWW / 2, mc_y)], (oc[0] - 60, oc[1]), f"res{y}{x}")
    # chain: i pin bank -> NI banks -> o
    pipe("u_pi", pin["i"], a.NI, 1, 1, [], (oc[0] - 60, oc[1]), "chain")
    # quads
    L = ["# hfd_attn_tile_b floorplan (tools/hbm_attn_die_tile_place.py): " +
         " ".join(f"{k}={getattr(a, k)}" for k in ("NK", "NC", "NR", "PMID", "NFC", "NFR", "NL", "NI"))]
    for (y, x), (x0, y0, o) in quads().items():
        L.append(f"place_macro -macro_name {{g_y\\[{y}\\].g_x\\[{x}\\].u_q}} -location {{{x0:.3f} {y0:.3f}}} -orientation {o} -exact")
    for n, o, x, y, w, h in P.banks:
        L.append(f"place_macro -macro_name {{{n}}} -location {{{x:.3f} {y:.3f}}} -orientation {o} -exact")
    L += ["foreach ot_i [[ord::get_db_block] getInsts] {",
          "  if {[[$ot_i getMaster] isBlock]} { $ot_i setPlacementStatus FIRM }",
          "}",
          f"puts \"OT_DIE_TILE_B_PLACED banks={len(P.banks)}\""]
    open(a.out, "w").write("\n".join(L) + "\n")
    bad = [h for h in hops if h[1] > a.max_hop]
    rec = dict(params={k: getattr(a, k) for k in ("NK", "NC", "NR", "PMID", "NFC", "NFR", "NL", "NI")},
               banks=len(P.banks), hops=hops, max_hop_um=max(h[1] for h in hops), over=bad,
               quads={f"{k[0]}{k[1]}": v for k, v in quads().items()})
    open(a.report, "w").write(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(banks=len(P.banks), max_hop=rec["max_hop_um"], over=bad)))
    for h in hops:
        print(h)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
