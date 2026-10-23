#!/usr/bin/env python3
"""A0-REPACK (10-23) candidate floorplans for the A0 ROM-leaf parents (NK / NL) + the rc14/rc15 baseline, as plan dicts
for flyline_model.py and the kit generator.  Every coordinate is in um, origins lower-left, orientation as in the spec."""
import json, re, math, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ROM_W, ROM_H, LSL_W, LSL_H, NODE_W, NODE_H = 172.8, 110.16, 99.792, 140.4, 47.52, 432.0
CM, PE, CH = 2.16, 20.0, 20.0          # core margin, pin-face edge band, children channel (ref_tile CHANNEL_UM)

def up(v, g):
    return round(math.ceil(v / g - 1e-9) * g, 4)

def bus_centroids(tcl):
    g = {}
    for m in re.finditer(r"place_pin -pin_name \{([^}]+)\} -layer (M\d) -location \{([\d.]+) ([\d.]+)\}", open(tcl).read()):
        b = "P_" + re.sub(r"\[\d+\]$", "", m.group(1)); g.setdefault(b, []).append((float(m.group(3)), float(m.group(4))))
    return {b: [round(sum(p[0] for p in v) / len(v), 2), round(sum(p[1] for p in v) / len(v), 2)] for b, v in g.items()}

def old(nk):
    s = json.load(open(ROOT / f"physical/ref_tile/qfd_tile_{'nk' if nk else 'nl'}_romleaf_rc15a/spec.json"))
    ch = {}
    for c in s["children"]:
        n = c["inst"]
        m = re.search(r"g_rb\[(\d)\]\.g_single\.g_col\[(\d)\]", n)
        if m: ch[f"ROM{m.group(2)}{m.group(1)}"] = [c["at"][0], c["at"][1], c["orient"]]
        m = re.search(r"g_sl\[(\d)\]", n)
        if m: ch[f"LSL{m.group(1)}"] = [c["at"][0], c["at"][1], c["orient"]]
        if "u_node" in n: ch["NODE"] = [c["at"][0], c["at"][1], c["orient"]]
    ports = bus_centroids(ROOT / f"tools/qwen_romleaf/rc14_2000/baseline/{'nk' if nk else 'nl'}_pins.tcl")
    return {"name": f"rc15_{'nk' if nk else 'nl'}", "outline": [s["outline"]["w"], s["outline"]["h"]], "children": ch,
            "ports": ports}

def cand_a(nk, W=457.92, rom_abut=True, lsl_abut=False, c_ab=30.0):
    """MAIN 'sandwich': S ROM group (banks 0-2, 3 rows) | LSL block (3 rows: col A R0 pins E, col B MY pins W + col C R0
    pins E back to back; NK node at the W face) | N ROM group (banks 3-4, 2 rows).  ROM rows: col 0 MY (pins E) | central
    spine | col 1 R0 (pins W)."""
    ch = {}
    # x: LSL block
    xn = up(CM + PE, 0.432)                      # node (W pins at the W face band)
    xa = up(xn + NODE_W + CH, 0.432)             # LSL col A, R0, pins E (bare W face toward the node's channel)
    xb = up(xa + LSL_W + c_ab, 0.432)            # col B, MY, pins W
    xc = round(xb + LSL_W, 3)                    # col C, R0, pins E -- abutted back to back with B (bare faces)
    ce = W - CM - (xc + LSL_W)
    assert ce >= PE - 1e-6, ("C_e", ce)
    # x: ROM rows, central spine aligned with C_ab
    x0 = up(CM + PE, 0.432)                       # ROM col 0 MY (pins E), bare W face 20 um off the W pin face
    x1 = round(W - CM - PE - ROM_W, 3)
    x1 = math.floor(x1 / 0.432 + 1e-9) * 0.432
    spine = x1 - (x0 + ROM_W)
    # y
    rp = ROM_H if rom_abut else up(ROM_H + CH, 2.16)
    y = up(CM + CH, 2.16)
    ys = [round(y + i * rp, 3) for i in range(3)]
    y = ys[-1] + ROM_H + CH
    y = up(y, 8.64)
    lp = up(LSL_H if lsl_abut else LSL_H + CH, 8.64) if not lsl_abut else LSL_H
    yl = [round(y + i * lp, 3) for i in range(3)]
    lsl_top = yl[-1] + LSL_H
    yn = up(lsl_top + CH, 2.16)
    yN = [round(yn + i * rp, 3) for i in range(2)]
    H = up(yN[-1] + ROM_H + CH + CM, 8.64)
    for b in range(3):
        ch[f"ROM0{b}"] = [x0, ys[b], "MY"]; ch[f"ROM1{b}"] = [x1, ys[b], "R0"]
    for b in range(2):
        ch[f"ROM0{b+3}"] = [x0, yN[b], "MY"]; ch[f"ROM1{b+3}"] = [x1, yN[b], "R0"]
    # LSLs: A rows 0-2 = g 0..2, B rows 0-2 = g 4..6, C rows 0-1 = g 3, 7 (C row 2 = the hub pocket at the tap face)
    for r in range(3):
        ch[f"LSL{r}"] = [xa, yl[r], "R0"]; ch[f"LSL{r+4}"] = [xb, yl[r], "MY"]
    ch["LSL3"] = [xc, yl[0], "R0"]; ch["LSL7"] = [xc, yl[1], "R0"]
    ylb = (yl[0] + lsl_top) / 2
    if nk:
        ch["NODE"] = [xn, up(ylb - NODE_H / 2, 2.16), "R0"]
    ports = {}
    # W face: NK n_a | n_b | t_out | n_y aligned with the node's a | b | t_out | y pins; NL t_out at the same rows
    yn0 = ch["NODE"][1] if nk else up(ylb - NODE_H / 2, 2.16)
    for b, ly in (("P_n_a", 60.6), ("P_n_b", 161.2), ("P_t_out", 261.7), ("P_n_y", 362.2)):
        if nk or b == "P_t_out": ports[b] = [0.0, round(yn0 + ly, 2)]
    # E face: tap / tile_id / rst_n beside the hub pocket (C row 2)
    ports["P_tap"] = [W, round(yl[2] + LSL_H / 2, 2)]
    ports["P_tile_id"] = [W, round(yl[2] + LSL_H - 10, 2)]
    ports["P_rst_n"] = [W, round(yl[2] + 10, 2)]
    return {"name": f"A_{'nk' if nk else 'nl'}", "outline": [W, H], "children": ch, "ports": ports,
            "geom": {"spine": round(spine, 3), "C_e": round(ce, 3), "C_ab": c_ab, "rom_abut": rom_abut,
                     "lsl_abut": lsl_abut, "ys": ys, "yN": yN, "yl": yl}}

def cand_b(nk, W=483.84, rom_abut=True, c_m=39.312):
    """FALLBACK 'wide two-tier': ROM block 5 rows (col 0 MY pins E | spine | col 1 R0 pins W; NK node at the W face beside
    the ROM rows) below an LSL block of 2 rows x 4 (MY|R0 back-to-back pairs, pins outward to the W / middle / E TX
    channels)."""
    ch = {}
    xn = up(CM + PE, 0.432)
    x0 = up(xn + NODE_W + CH, 0.432)            # node in every variant's outline (NL: that band is std rows)
    x1 = math.floor((W - CM - PE - ROM_W) / 0.432 + 1e-9) * 0.432
    spine = x1 - (x0 + ROM_W)
    rp = ROM_H if rom_abut else up(ROM_H + CH, 2.16)
    y0 = up(CM + CH, 2.16)
    yr = [round(y0 + i * rp, 3) for i in range(5)]
    order = [0, 1, 2, 3, 4]
    for i, b in enumerate(order):
        ch[f"ROM0{b}"] = [x0, yr[i], "MY"]; ch[f"ROM1{b}"] = [x1, yr[i], "R0"]
    ytop = yr[-1] + ROM_H
    yl0 = up(ytop + CH + 20.0, 8.64)            # hub / operand band between the ROM block and the LSL block
    yl = [yl0, up(yl0 + LSL_H + CH, 8.64)]
    cw = up(CM + PE, 0.432)
    xs = [cw, round(cw + LSL_W, 3)]
    xm = up(xs[1] + LSL_W + c_m, 0.432)
    xs += [xm, round(xm + LSL_W, 3)]
    ce = W - CM - (xs[3] + LSL_W)
    assert ce >= PE - 1e-6, ("C_e", ce)
    g = 0
    for r in range(2):
        for c in range(4):
            ch[f"LSL{[0,1,4,5][c] + 2*r if False else (c*2 + r)}"] = [xs[c], yl[r], "MY" if c % 2 == 0 else "R0"]
    H = up(yl[1] + LSL_H + CH + CM, 8.64)
    if nk:
        ch["NODE"] = [xn, up(yr[1], 2.16), "R0"]
    yn0 = ch["NODE"][1] if nk else up(yr[1], 2.16)
    ports = {}
    for b, ly in (("P_n_a", 60.6), ("P_n_b", 161.2), ("P_t_out", 261.7), ("P_n_y", 362.2)):
        if nk or b == "P_t_out": ports[b] = [0.0, round(yn0 + ly, 2)]
    ports["P_tap"] = [W, round(ytop + 30, 2)]
    ports["P_tile_id"] = [W, round(ytop + 40, 2)]
    ports["P_rst_n"] = [W, round(ytop + 20, 2)]
    return {"name": f"B_{'nk' if nk else 'nl'}", "outline": [W, H], "children": ch, "ports": ports,
            "geom": {"spine": round(spine, 3), "C_e": round(ce, 3), "C_m": c_m, "rom_abut": rom_abut}}

def area_report(p):
    W, H = p["outline"]
    hard = sum((172.8 * 110.16 if k.startswith("ROM") else 99.792 * 140.4 if k.startswith("LSL") else 47.52 * 432)
               for k in p["children"])
    return {"W": W, "H": H, "area_mm2": round(W * H / 1e6, 4), "hard_um2": round(hard), "hard_fill": round(hard / (W * H), 3)}

if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    import flyline_model as FM
    cen = {k: json.load(open(sys.argv[1] if k == "nl" else sys.argv[2])) for k in ("nl", "nk")}
    for nk in (False, True):
        k = "nk" if nk else "nl"
        for p in (old(nk), cand_a(nk), cand_a(nk, rom_abut=False), cand_a(nk, W=449.28, lsl_abut=True),
                  cand_b(nk), cand_b(nk, rom_abut=False)):
            r = FM.solve(cen[k], p)
            print(p["name"], area_report(p), p.get("geom", {}).get("spine"), "bit-mm", r["bit_mm"],
                  {c: v["max_um"] for c, v in list(r["classes"].items())[:6]})

def cand_a2(nk, W=457.92, rom_abut=True, c_ab=30.0, band=40.0):
    """MAIN (457.92 wide = the CB16 x budget): two tiers in y.  ROM block at the bottom: 5 ROM rows (col 0 MY pins E |
    central spine | col 1 R0 pins W), S group (banks 0-2) at the bottom, N group (banks 3-4) on top next to the operand
    band; operand band (rings, operand registers, L2C, hub; tap pins on its E end); LSL block on top: 3 rows x 3 columns
    (A R0 pins E | TX channel | B MY pins W + C R0 pins E back to back | E channel), NK node at the W face beside col A.
    Col C rows 1-2 hold LSL 3 / 7; its row 0 slot is the hub pocket at the operand band and the E (tap) face."""
    ch = {}
    x0 = up(CM + PE, 0.432)
    x1 = math.floor((W - CM - PE - ROM_W) / 0.432 + 1e-9) * 0.432
    spine = x1 - (x0 + ROM_W)
    rp = ROM_H if rom_abut else up(ROM_H + CH, 2.16)
    y0 = up(CM + CH, 2.16)
    order = [0, 1, 2, 4, 3]                        # bottom -> top: S group, then N group with bank 3 at the band
    yr = [round(y0 + i * rp, 3) for i in range(5)]
    for i, b in enumerate(order):
        ch[f"ROM0{b}"] = [x0, yr[i], "MY"]; ch[f"ROM1{b}"] = [x1, yr[i], "R0"]
    ytop = yr[-1] + ROM_H
    yl0 = up(ytop + band, 8.64)
    lp = up(LSL_H + CH, 8.64)
    yl = [yl0, round(yl0 + lp, 3), round(yl0 + 2 * lp, 3)]
    xn = up(CM + PE, 0.432)
    xa = up(xn + NODE_W + CH, 0.432)
    xb = up(xa + LSL_W + c_ab, 0.432)
    xc = round(xb + LSL_W, 3)
    ce = W - CM - (xc + LSL_W)
    assert ce >= PE - 1e-6, ("C_e", ce)
    for r in range(3):
        ch[f"LSL{r}"] = [xa, yl[r], "R0"]; ch[f"LSL{r+4}"] = [xb, yl[r], "MY"]
    ch["LSL3"] = [xc, yl[1], "R0"]; ch["LSL7"] = [xc, yl[2], "R0"]
    lsl_top = yl[2] + LSL_H
    H = up(lsl_top + CH + CM, 8.64)
    ylb = (yl[0] + lsl_top) / 2
    yn0 = up(ylb - NODE_H / 2, 2.16)
    if nk:
        ch["NODE"] = [xn, yn0, "R0"]
    ports = {}
    for b, ly in (("P_n_a", 60.6), ("P_n_b", 161.2), ("P_t_out", 261.7), ("P_n_y", 362.2)):
        if nk or b == "P_t_out": ports[b] = [0.0, round(yn0 + ly, 2)]
    ports["P_tap"] = [W, round(ytop + band / 2 + 40, 2)]
    ports["P_tile_id"] = [W, round(ytop + band / 2 + 100, 2)]
    ports["P_rst_n"] = [W, round(ytop + band / 2 + 110, 2)]
    return {"name": f"A2_{'nk' if nk else 'nl'}", "outline": [W, H], "children": ch, "ports": ports,
            "geom": {"spine": round(spine, 3), "C_e": round(ce, 3), "C_ab": c_ab, "rom_abut": rom_abut, "yr": yr,
                     "yl": yl, "band": [ytop, yl0]}}

def cand_b2(nk, W=483.84, rom_abut=False, c_m=39.312, band=40.0):
    """FALLBACK (no tool opt-in): cand_b with the ROM rows N group next to the operand band and 20-um ROM row channels."""
    p = cand_b(nk, W=W, rom_abut=rom_abut, c_m=c_m)
    ys = sorted({v[1] for k, v in p["children"].items() if k.startswith("ROM0")})
    for i, b in enumerate([0, 1, 2, 4, 3]):
        p["children"][f"ROM0{b}"][1] = ys[i]; p["children"][f"ROM1{b}"][1] = ys[i]
    p["name"] = f"B2_{'nk' if nk else 'nl'}"
    return p

if __name__ == "__main__" and len(sys.argv) > 3:
    import flyline_model as FM
    cen = {k: json.load(open(sys.argv[1] if k == "nl" else sys.argv[2])) for k in ("nl", "nk")}
    for nk in (False, True):
        k = "nk" if nk else "nl"
        for p in (old(nk), cand_a2(nk), cand_b2(nk), cand_b2(nk, rom_abut=True)):
            r = FM.solve(cen[k], p)
            print(p["name"], area_report(p), "bit-mm", r["bit_mm"], {c: (v["bit_mm"], v["max_um"]) for c, v in list(r["classes"].items())[:5]})

def g(v, q):            # snap up to grid q (um), exact decimal
    return round(math.ceil(round(v / q, 6) - 1e-9) * q, 4)

ROM_PITCH_GRID = 0.048          # ROM signal pins are M4 (horizontal, 0.048): origin y on 0.048 keeps them on track
LSL_Y_GRID = 0.192              # LSL pins M4 + M6 (0.048 / 0.064): lcm 0.192
X_GRID = 0.432                  # site 0.054 x M5 0.048

def cand_c(nk, W=457.92):
    """MAIN 'C' (A0-REPACK 10-23).  Two tiers, CB16 corridor budget unchanged (W <= 457.92, H <= 1166.4):
    ROM block (bottom): 5 rows of a back-to-back pair -- col 0 R0 (pins W) | col 1 MY (pins E), bare E/W faces abutted
    (abutted_row) -- so both pin faces open into one W and one E operand channel of (W - 345.6 - 2*2.16)/2 = 54 um, which
    hold the bank OR-trees / landing rings / operand readers of their own column (no dead spine, no sliver).
    Rows bottom->top: banks 0,1,2 (S group) then 4,3 (N group; bank 3 next to the band).  20-um (on-grid) row channels.
    LSL block (top): 3 rows x [col A R0 pins E | TX channel | col B MY pins W + col C R0 pins E back to back | E TX
    channel]; NK node at the W face beside col A (its a/b/t_out/y pins face the tile W face, t_d faces the TX channel).
    Col C row 0 = hub pocket (tap pins on the E face beside it)."""
    ch = {}
    x0 = g((W - 2 * ROM_W) / 2, X_GRID)
    x1 = round(x0 + ROM_W, 4)
    cw = x0 - CM; ce = W - CM - (x1 + ROM_W)
    assert cw >= PE - 1e-6 and ce >= PE - 1e-6, (cw, ce)
    y0 = g(CM + CH, ROM_PITCH_GRID)
    rp = g(ROM_H + CH, ROM_PITCH_GRID)
    yr = [round(y0 + i * rp, 4) for i in range(5)]
    for i, b in enumerate([0, 1, 2, 4, 3]):
        ch[f"ROM0{b}"] = [x0, yr[i], "R0"]; ch[f"ROM1{b}"] = [x1, yr[i], "MY"]
    rtop = yr[-1] + ROM_H
    yl0 = g(rtop + CH, 8.64)
    lp = g(LSL_H + CH, LSL_Y_GRID)
    yl = [round(yl0 + i * lp, 4) for i in range(3)]
    ltop = yl[-1] + LSL_H
    H = g(ltop + CH + CM, 8.64)
    xn = g(CM + PE, X_GRID)
    xa = g(xn + NODE_W + CH, X_GRID)
    # col B + C pair right-aligned to the E pin band; the A-B TX channel takes the rest
    xc = round(math.floor((W - CM - PE - LSL_W) / X_GRID + 1e-9) * X_GRID, 4)
    xb = round(xc - LSL_W, 4)
    c_ab = xb - (xa + LSL_W)
    assert c_ab >= CH - 1e-6, c_ab
    for r in range(3):
        ch[f"LSL{r}"] = [xa, yl[r], "R0"]; ch[f"LSL{r+4}"] = [xb, yl[r], "MY"]
    ch["LSL3"] = [xc, yl[1], "R0"]; ch["LSL7"] = [xc, yl[2], "R0"]
    yn0 = g((yl[0] + ltop) / 2 - NODE_H / 2, ROM_PITCH_GRID)
    if nk:
        ch["NODE"] = [xn, yn0, "R0"]
    ports = {}
    for b, ly in (("P_n_a", 60.6), ("P_n_b", 161.2), ("P_t_out", 261.7), ("P_n_y", 362.2)):
        if nk or b == "P_t_out": ports[b] = [0.0, round(yn0 + ly, 2)]
    ports["P_tap"] = [W, round(yl[0] + LSL_H / 2, 2)]
    ports["P_tile_id"] = [W, round(yl[0] + LSL_H - 10, 2)]
    ports["P_rst_n"] = [W, round(yl[0] + 10, 2)]
    return {"name": f"C_{'nk' if nk else 'nl'}", "outline": [W, H], "children": ch, "ports": ports,
            "geom": {"cw": round(cw, 3), "ce": round(ce, 3), "c_ab": round(c_ab, 3), "yr": yr, "yl": yl,
                     "band": [round(rtop, 3), yl0], "rom_x": [x0, x1], "lsl_x": [xa, xb, xc], "node": [xn, yn0]}}

def cand_d(nk, W=483.84):
    """FALLBACK 'D': as C but the LSL block is 2 rows x 4 (two MY|R0 back-to-back pairs: pins W | TX channel between the
    pairs | pins E), shorter and 26 um wider (CB16 corridors give 4 x 25.9 um in x and get 4 x ~120 um in y back)."""
    ch = {}
    x0 = g((W - 2 * ROM_W) / 2, X_GRID); x1 = round(x0 + ROM_W, 4)
    y0 = g(CM + CH, ROM_PITCH_GRID); rp = g(ROM_H + CH, ROM_PITCH_GRID)
    yr = [round(y0 + i * rp, 4) for i in range(5)]
    for i, b in enumerate([0, 1, 2, 4, 3]):
        ch[f"ROM0{b}"] = [x0, yr[i], "R0"]; ch[f"ROM1{b}"] = [x1, yr[i], "MY"]
    rtop = yr[-1] + ROM_H
    yl0 = g(rtop + CH, 8.64); lp = g(LSL_H + CH, LSL_Y_GRID)
    yl = [round(yl0 + i * lp, 4) for i in range(2)]
    ltop = yl[-1] + LSL_H
    H = g(ltop + CH + CM, 8.64)
    xs0 = g(CM + PE, X_GRID)
    xs3 = round(math.floor((W - CM - PE - LSL_W) / X_GRID + 1e-9) * X_GRID, 4)
    xs = [xs0, round(xs0 + LSL_W, 4), round(xs3 - LSL_W, 4), xs3]
    cm = xs[2] - (xs[1] + LSL_W)
    assert cm >= CH - 1e-6, cm
    for r in range(2):
        for c in range(4):
            ch[f"LSL{c * 2 + r}"] = [xs[c], yl[r], "MY" if c % 2 == 0 else "R0"]
    if nk:     # node in the W ROM channel?  no: 47.5 wide + its pin bands do not fit 54 um; it sits in the TX channel
        raise NotImplementedError("D NK: node placement")
    ports = {"P_t_out": [0.0, round(yl[0] + 70, 2)], "P_tap": [W, round(rtop + 10, 2)],
             "P_tile_id": [W, round(rtop + 14, 2)], "P_rst_n": [W, round(rtop + 6, 2)]}
    return {"name": f"D_{'nk' if nk else 'nl'}", "outline": [W, H], "children": ch, "ports": ports,
            "geom": {"cm": round(cm, 3), "yr": yr, "yl": yl}}

if __name__ == "__main__" and len(sys.argv) > 4:
    import flyline_model as FM
    cen = {k: json.load(open(sys.argv[1] if k == "nl" else sys.argv[2])) for k in ("nl", "nk")}
    for nk in (False, True):
        k = "nk" if nk else "nl"
        ps = [old(nk), cand_c(nk)] + ([] if nk else [cand_d(nk)])
        for p in ps:
            r = FM.solve(cen[k], p)
            print(p["name"], area_report(p), p.get("geom"), "\n   bit-mm", r["bit_mm"], {c: (v["bit_mm"], v["max_um"]) for c, v in list(r["classes"].items())[:8]})
