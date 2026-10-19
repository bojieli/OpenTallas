#!/usr/bin/env python3
"""HBM-NEXT-SM4 (10-19 06:xx): ref_tile spec for the NARROW lever (a) SM P = 4 tile hnx_rp4lp4n = hnx_rp4lp4x (same RTL top
hnx_rp4lp4x_flat_lp, same ports / pins / regions / landings / stations, same CLOSED-view children, same hnx_xs4 W / E face split)
re-packed to the DIE frame width 673.92 um (the 1080-wide hnx_rp4lp4x leaf does not fit the DIE lattice row).

  leaf (R0, leaf 0 above the middle band; leaf 1 below it mirrored MX, tct kept R0):

     x: 43.2           241.92             432.0          630.72
        +--------------+                  +--------------+
        | lane 1 stack |                  | lane 3 stack |     row 2 (dy 695.52)
        +--------------+                  +--------------+
        | lane 0 stack |                  | lane 2 stack |     row 1 (dy 468.72)      BF16: tct + 2 tcl, d4g arrangement
        +--------------+                  +--------------+
     W  |ch| bdc0   bdc1   bdc2   bdc3          |ch|  E          bdc row (dy 315.36), 4 x 112.32 at 129.6 pitch (N face block-dot)
        |  | hnx_xs4 501.12 x 289.44 (86.4..587.52)|  |          store (dy 0) faces the band: S landing inputs
        43.2-um operand channels W / E of the store + bdc row (BF16 operands of lanes 0-1 W, 2-3 E: the existing face split)

  * leaf 911.52 tall; middle band 237.6 (beat 216 + 2 x 10.8; land / row_w / row_e top + bottom as hnx_rp4lp4x);
  * outline 673.92 x 2,181.6 (all y on the 4.32 lattice), 30.24 margins / band gaps.

  python3 tools/hbm_next/sm4/hnx_rp4lp4n_kit.py [rp4lp_spec rp4lp_pins rp4lp_stations]
        -> physical/hbm_next/sm4/hnx_rp4lp4n_spec.json (+ pins / stations tcl)
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("kx", HERE / "hnx_rp4lp4x_kit.py")
kx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kx)

NAME = "hnx_rp4lp4n"
W = 673.92
X0 = 43.2                                   # leaf origin (tile W margin)
XS_DX = 43.2                                # store x inside the leaf: 43.2-um W operand channel
GAP = 10.8                                  # bdc row -> stack row, stack row -> stack row (halo)
ROW1 = kx.SZ["xs4"][1] + kx.GAP_ST + kx.SZ["bdc"][1] + GAP
ROW2 = ROW1 + kx.STACK_H + GAP
LEAF_H = ROW2 + kx.STACK_H
XE_DX = (W - X0) - X0 - kx.STACK_W          # E stacks end 43.2 from the tile E edge
M = 30.24                                   # tile margin and leaf <-> band gap
HM = 237.6
Y_L1 = M
Y_M = Y_L1 + LEAF_H + M
Y_L0 = Y_M + HM + M
H = round(Y_L0 + LEAF_H + M, 3)


def leaf_children():
    out = [("xs4", "g_xs.u_xs", XS_DX, 0.0)]
    by = kx.SZ["xs4"][1] + kx.GAP_ST
    for p in range(kx.P):
        out.append(("bdc", f"g_ln[{p}].u_bdc", XS_DX + 129.6 * p, by))
    # lanes 0 / 1 W (rows 1 / 2), lanes 2 / 3 E: matches the store's W / E face split (PW = 2)
    for p, (sx, sy) in enumerate(((0.0, ROW1), (0.0, ROW2), (XE_DX, ROW1), (XE_DX, ROW2))):
        out += [("tct", f"g_ln[{p}].u_tcc.u_tr", sx, sy),
                ("tcl", f"g_ln[{p}].u_tcc.u_h0", sx, sy + 95.04),
                ("tcl", f"g_ln[{p}].u_tcc.u_h1", sx + 112.32, sy + 95.04)]
    return out


def children():
    out = []
    r3 = kx.r3
    for leaf, y0, orient, reg in ((0, Y_L0, "R0", "n"), (1, Y_L1, "MX", "s")):
        for kind, sub, dx, dy in leaf_children():
            h = kx.SZ[kind][1]
            y = y0 + dy if orient == "R0" else y0 + LEAF_H - dy - h
            o = "R0" if kind == "tct" else orient
            out.append(dict(view=kx.V[kind], count=1, at=[r3(X0 + dx), r3(y)], orient=o, inst=f"u_lf{leaf}.{sub}", region=reg))
    m = Y_M
    xs = X0 + XS_DX
    out += [dict(view=kx.V["beat"], count=1, at=[43.2, r3(m + 10.8)], orient="R0", inst="u_beat_t", region="n"),
            dict(view=kx.V["row_w"], count=1, at=[r3(xs + 17.28), r3(m)], orient="MX", inst="u_row1", region="s"),
            dict(view=kx.V["row_w"], count=1, at=[r3(xs + 17.28), r3(m + HM - 90.72)], orient="R0", inst="u_row0", region="n"),
            dict(view=kx.V["land"], count=1, at=[r3(xs + 190.08), r3(m)], orient="MX", inst="u_land_s", region="s"),
            dict(view=kx.V["land"], count=1, at=[r3(xs + 190.08), r3(m + HM - 43.2)], orient="R0", inst="u_land_n", region="n"),
            dict(view=kx.V["beat"], count=1, at=[r3(W - 129.6), r3(m + 10.8)], orient="R0", inst="u_beate", region="n"),
            dict(view=kx.V["row_e"], count=1, at=[r3(W - 69.12), r3(m)], orient="MX", inst="u_rowe1", region="s"),
            dict(view=kx.V["row_e"], count=1, at=[r3(W - 69.12), r3(m + HM - 90.72)], orient="R0", inst="u_rowe0", region="n")]
    return out


def main():
    # re-point the lever-(a) generator at this floorplan (its pins / stations / spec code reads these globals)
    for k, v in dict(NAME=NAME, W=W, H=H, X0=X0, XS_DX=XS_DX, XE_DX=XE_DX, LEAF_H=LEAF_H, Y_L1=Y_L1, Y_M=Y_M, HM=HM,
                     Y_L0=Y_L0, DY_PINS=(Y_M + HM / 2) - kx.RP4LP_PIN_YC).items():
        setattr(kx, k, v)
    kx.leaf_children = leaf_children
    kx.children = children
    for a in (Y_L1, Y_M, Y_L0, H, X0 + XS_DX, X0 + XE_DX):
        assert abs(a / 4.32 - round(a / 4.32)) < 1e-6, a
    kx.main()
    p = kx.OUTD / f"{NAME}_spec.json"
    s = json.loads(p.read_text())
    s["job"]["tag"] = NAME
    s["job"]["structural_change"] = (
        f"{NAME} (HBM-NEXT-SM4 10-19) = hnx_rp4lp4x (same RTL, pins, regions, landings, children) re-packed to the DIE frame width "
        f"{W}: per leaf hnx_xs4 at the band (S landing), 4 bdc in one row on its N face, the 4 BF16 lane stacks in two rows above "
        f"the bdc row (lanes 0-1 W, 2-3 E, fed by the store's W / E faces through 43.2-um operand channels); outline {W} x {H}, "
        f"leaf {LEAF_H:.2f}, middle band {HM}.")
    p.write_text(json.dumps(s, indent=1) + "\n")
    # operand route reach (store face register -> farthest consumer macro edge), um, Manhattan
    reach = {"bf16_row1_um": round(ROW1 - kx.SZ["xs4"][1] / 2 + XS_DX, 1),
             "bf16_row2_um": round(ROW2 - kx.SZ["xs4"][1] / 2 + XS_DX, 1)}
    print(json.dumps({"leaf_h": round(LEAF_H, 3), "band": HM, "H": H, "reach": reach}))


if __name__ == "__main__":
    main()
