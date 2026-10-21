#!/usr/bin/env python3
"""RP4c: every hard-child clock entry at its child's clock pin; same RTL / data edges as RP4 / RP4b.

Measured RP4b CTS gate (smh_tile_rp4b-20261016-040329, EPYC4): all 28 clock ports sat on the W face at arbitrary y, so
17 of 18 one-port/one-pin hard entries were unbuffered 104-791 um wires (clock_entries.tcl LONG > 60 um): TT 39-1,161 ps,
slews 124-3,682 ps (clk_hard[17] pte.u_beat 791 um).  RP4c places each entry pin on the parent face at the projection of
the child's actual LEF clock pin and arranges the children so that every clock pin faces a parent face:
  * leaf 0 (north) keeps the RP4b leaf geometry; leaf 1 (south) is its exact mirror (MX), so its BF16 columns' clock
    pins face the S face like leaf 0's face N, and its column tree's clock faces E like leaf 0's;
  * the input-side beat group (u_ptw.u_beat_t) moves into the W column between the two row groups, aligned with the
    E beat group, so bin -> pin flop -> beat_t.d and beat_t.last -> pte.u_beat.d are straight and its clock is at W;
  * every row / beat / land group sits in a face column with its clock corner on that face;
  * the two transport lands sit directly beside their x stores (bk1 straight), rows aligned W/E (rpm straight).
The only entries over 60 um are the two x stores (LEF clock pin 122.7 um from the store's west edge on its north edge;
reaching it from any face is >= 148.6 um without a child re-pin).  Outline grows 95.04 um in height (406.08 x 1529.28)
to fit the W column (land, row, beat, row, land).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/hier_contract"))
from child_lint import parse_lef  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from repack import stats, draw  # noqa: E402

W, H = 406.08, 1529.28
M4 = lambda k: round(0.012 + 0.048 * k, 3)  # noqa: E731  W/E pin track (horizontal M4)
M5 = M4                                       # N/S pin track (vertical M5), same 48 nm lattice


def k_of(v):
    return round((v - 0.012) / 0.048)


V = {
    "xs": "physical/ref_tile/smh_xs_ref_p45m/views/ot_hbm_accel_smh_xs",
    "bdc": "physical/ref_tile/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc",
    "tcl": "physical/ref_tile/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl",
    "tct": "physical/ref_tile/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct",
    "row_w": "physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w",
    "row_e": "physical/ref_tile/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e",
    "beat": "physical/ref_tile/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e",
    "land": "physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land",
}
# (inst, master, x, y, orient, entry port, entry face)
LF0 = [  # north leaf = RP4b geometry, offsets from the top face unchanged
    ("u.g_lf?0?.u_lh.u_xs", "xs", 25.92, H - 457.92, "R0", "clk_hard[0]", "W"),
    ("u.g_lf?0?.u_lh.u_bdc", "bdc", 25.92, H - 241.92, "R0", "clk_hard[1]", "W"),
    ("u.g_lf?0?.u_lh.u_tcc.u_h0", "tcl", 164.16, H - 146.88, "R0", "clk_hard[2]", "N"),
    ("u.g_lf?0?.u_lh.u_tcc.u_h1", "tcl", 276.48, H - 146.88, "R0", "clk_hard[3]", "N"),
    ("u.g_lf?0?.u_lh.u_tcc.u_tr", "tct", 164.16, H - 241.92, "R0", "clk_hard[4]", "E"),
]
FLIP = {"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"}
FACE = {"N": "S", "S": "N", "W": "W", "E": "E"}
SIZE = {}
LEF = {}
for k, v in V.items():
    p = ROOT / v / (Path(v).name + ".lef")
    LEF[k] = parse_lef(p.read_text())
    SIZE[k] = (LEF[k]["W"], LEF[k]["H"])
LF1 = []
for i, (inst, m, x, y, o, port, face) in enumerate(LF0):
    n = int(re.search(r"clk_hard\[(\d+)\]", port)[1]) + 5
    LF1.append((inst.replace("g_lf?0?", "g_lf?1?"), m, x, round(H - y - SIZE[m][1], 3), FLIP[o], f"clk_hard[{n}]", FACE[face]))
# The column tree (tct) LEF has 18 W-face M4 pins that no origin puts on the M4 tracks when it is mirrored in y (MX /
# R180: macro_grid FAIL, measured at gen), so leaf 1 keeps it R0: clock on its S edge (E face, 72.7 um), sum_i on its N
# edge; the BF16 columns' sum_o (MX, top) reach it through the 47.5 um channel left of it.
LF1 = [t if t[1] != "tct" else (t[0], "tct", 185.76, t[3], "R0", t[5], "E") for t in LF1]
XE = 336.96
MID = [
    ("u.u_ptw.u_land_s", "land", 25.92, 479.52, "MX", "clk_hard[16]", "W"),
    ("u.u_ptw.u_row1", "row_w", 25.92, 544.32, "MX", "clk_hard[11]", "W"),
    ("u.u_ptw.u_beat_t", "beat", 25.92, 656.64, "R0", "clk_hard[14]", "W"),
    ("u.u_ptw.u_row0", "row_w", 25.92, 894.24, "R0", "clk_hard[10]", "W"),
    ("u.u_ptw.u_land_n", "land", 25.92, 1006.56, "R0", "clk_hard[15]", "W"),
    ("u.u_pte.u_row1", "row_e", XE, 544.32, "MX", "clk_hard[13]", "E"),
    ("u.u_pte.u_beat", "beat", XE, 656.64, "R0", "clk_hard[17]", "E"),
    ("u.u_pte.u_row0", "row_e", XE, 894.24, "R0", "clk_hard[12]", "E"),
]
# a mirrored (MX / R180) child keeps its M4 pins on the parent's 48 nm track lattice only at origin y = 0.024 mod 0.048
# (all eight masters have heights on the 48 nm lattice); ref_tile's track-alignment shift does the same (RP4b land_s
# 717.12 -> 717.144), so the spec carries it explicitly and every derived pin uses the placed origin.
def _snap(t):
    inst, m, x, y, o, port, face = t
    if o in ("MX", "R180"):
        y = round(round((y - 0.024) / 0.048) * 0.048 + 0.024, 3)
    return (inst, m, x, y, o, port, face)


CH = [_snap(t) for t in LF0 + LF1 + MID]
# ref_tile's on-track origin (macro_grid_lint best_shift, measured at gen) for the leaf-1 children; pins derive from it
PLACED_Y = {"u.g_lf?1?.u_lh.u_xs": 298.104, "u.g_lf?1?.u_lh.u_bdc": 99.36, "u.g_lf?1?.u_lh.u_tcc.u_h0": 25.92,
            "u.g_lf?1?.u_lh.u_tcc.u_h1": 25.92, "u.g_lf?1?.u_lh.u_tcc.u_tr": 168.576}
CH = [t if t[0] not in PLACED_Y else (t[0], t[1], t[2], PLACED_Y[t[0]], *t[4:]) for t in CH]


def xform(m, x, y, o, px, py):
    w, h = SIZE[m]
    if o in ("MY", "R180"):
        px = w - px
    if o in ("MX", "R180"):
        py = h - py
    return x + px, y + py


def pin_center(m, x, y, o, pin, edge=None):
    rr = LEF[m]["pins"][pin]["rects"]
    if edge is not None:
        rr = [r for r in rr if edge(r, *SIZE[m])]
    assert rr, (m, pin)
    _, x0, y0, x1, y1 = rr[0]
    return xform(m, x, y, o, (x0 + x1) / 2, (y0 + y1) / 2)


spec = json.loads((ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4b.json").read_text())
old = {c["inst"]: c for c in spec["children"]}
children, boxes = [], []
for inst, m, x, y, o, port, face in CH:
    c = dict(old[inst])
    assert c["view"] == V[m], (inst, c["view"])
    c.update(at=[round(x, 3), round(y, 3)], orient=o)
    children.append(c)
    boxes.append(("row" if m.startswith("row") else m, inst, x, y, *SIZE[m]))
assert len(children) == len(old) == 18
st = stats(W, H, boxes)
assert not st["overlaps"] and not st["slivers_um"], st

# ---- data pins: rout/bout at the actual E-edge output bit of the hard row / beat cell, rin/bin at the same y on W
pins, links = {}, []
east = lambda r, w, h: r[3] >= w - 0.001  # noqa: E731
for inst, base, count, outp, inp in [("u.u_pte.u_row0", 0, 818, "rout", "rin"), ("u.u_pte.u_row1", 818, 818, "rout", "rin"),
                                     ("u.u_pte.u_beat", 0, 2069, "bout", "bin")]:
    _, m, x, y, o, _, _ = next(t for t in CH if t[0] == inst)
    for bit in range(count):
        layer = LEF[m]["pins"][f"last[{bit}]"]["rects"][0][0]
        assert layer == "M4"
        px, py = pin_center(m, x, y, o, f"last[{bit}]", east)
        py = round(py, 6)
        assert abs(px - (x + SIZE[m][0])) < 0.2 and abs((py - 0.012) / 0.048 - k_of(py)) < 1e-4, (inst, bit, px, py)
        for port, fx in [(outp, W), (inp, 0.0)]:
            pins[f"{port}[{base + bit}]"] = ("M4", fx, py)
        links.append({"parent": f"{outp}[{base + bit}]", "child": f"{inst}/last[{bit}]", "y_um": py,
                      "horizontal_stub_um": round(W - px, 3)})
        # the paired W input must face the same-bit input of the W row / beat group (straight rin -> pin flop -> d)
    wi = {"u.u_pte.u_row0": "u.u_ptw.u_row0", "u.u_pte.u_row1": "u.u_ptw.u_row1", "u.u_pte.u_beat": "u.u_ptw.u_beat_t"}[inst]
    _, mw, xw, yw, ow, _, _ = next(t for t in CH if t[0] == wi)
    for bit in (0, count // 2, count - 1):
        _, wy = pin_center(mw, xw, yw, ow, f"d[{bit}]", lambda r, w, h: r[1] <= 0.001)
        assert abs(wy - pins[f"{inp}[{base + bit}]"][2]) < 0.05, (inst, wi, bit, wy)

used = {"W": set(), "E": set(), "N": set(), "S": set()}
for p, (layer, x, y) in pins.items():
    used["E" if x > 0 else "W"].add(k_of(y))

# ---- keep the remaining RP4b data pins (N: gin / xs_* / rst_n, S: gout); move N to the new top face
pat = re.compile(r"place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([^ ]+) ([^}]+)\}")
other = []
for line in (ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4b_pins.tcl").read_text().splitlines():
    mm = pat.search(line)
    if not mm:
        continue
    port, layer, x, y = mm[1], mm[2], float(mm[3]), float(mm[4])
    if port in pins or port.startswith(("clk_hard[", "clk_pin[", "clk_oper[", "clk_region[")):
        continue
    assert layer == "M5" and y in (0.0, 1434.24), (port, layer, x, y)
    face = "N" if y > 0 else "S"
    other.append((port, layer, x, H if face == "N" else 0.0))
    used[face].add(k_of(x))


def free_track(face, want, gap=3):
    k0 = k_of(want)
    for d in range(0, 4000):
        for k in (k0 - d, k0 + d):
            if k > 3 and all(abs(k - u) > gap for u in used[face]):
                lim = (W if face in "NS" else H) - 0.2
                if 0.2 < M4(k) < lim:
                    used[face].add(k)
                    return M4(k)
    raise SystemExit(f"no free {face} track near {want}")


# ---- clock entries: one port per hard-child clock pin, at its projection on the chosen face
clk_lines, entries = [], []
for inst, m, x, y, o, port, face in CH:
    cx, cy = pin_center(m, x, y, o, "clk")
    if face in "WE":
        py = free_track(face, cy)
        px = 0.0 if face == "W" else W
        wire = abs(px - cx) + abs(py - cy)
        clk_lines.append((port, "M4", px, py))
    else:
        px = free_track(face, cx)
        py = H if face == "N" else 0.0
        wire = abs(px - cx) + abs(py - cy)
        clk_lines.append((port, "M5", px, py))
    entries.append({"port": port, "child": inst + "/clk", "face": face, "child_clk_um": [round(cx, 3), round(cy, 3)],
                    "pin_um": [px, py], "manhattan_um": round(wire, 2)})

# ---- glue CTS roots: at the face next to their sinks (sink groups named by the RTL, rp4 clocks source)
SOFT = [
    ("clk_pin[1]", "W", 638.0, "row1 rin pin flops (W window 550-629)"),
    ("clk_pin[2]", "W", 652.0, "bin pin flops (W window 666-864)"),
    ("clk_pin[0]", "W", 888.0, "row0 rin pin flops (W window 900-979)"),
    ("clk_oper[0]", "W", H - 271.28, "leaf0 xb stations, x store | block-dot gap"),
    ("clk_oper[1]", "E", H - 271.28, "leaf0 xf stations, centre channel to the BF16 columns"),
    ("clk_oper[2]", "W", 271.28, "leaf1 xb stations (mirror)"),
    ("clk_oper[3]", "E", 271.28, "leaf1 xf stations (mirror)"),
    ("clk_region[0]", "W", H - 179.28, "leaf0 leaf clock + north G1/reset/strap stages"),
    ("clk_region[1]", "E", 1028.0, "middle G2 / reset stages"),
    ("clk_region[2]", "W", 179.28, "leaf1 leaf clock + south G / gout stages"),
]
for port, face, want, why in SOFT:
    py = free_track(face, want)
    clk_lines.append((port, "M4", 0.0 if face == "W" else W, py))
    entries.append({"port": port, "glue_root": True, "face": face, "pin_um": [0.0 if face == "W" else W, py], "sinks": why})

lines = ["# generated by tools/hbm_sm_repack_1015/rp4c_entry_successor.py: RP4c pin plan; rin/bin at the SAME y as the",
         "# actual E-edge output bit of the hard row / beat cell (rout/bout); each hard clock entry at its child's clock pin"]


def fmt(port, layer, x, y):
    size = "{0.192 0.024}" if layer == "M4" else "{0.024 0.192}"
    return f"place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {size} -force_to_die_boundary"


order = sorted(pins.items(), key=lambda t: (t[0].split("[")[0], int(t[0].split("[")[1][:-1])))
lines += [fmt(p, *v) for p, v in order]
lines += [fmt(*t) for t in other]
lines += [fmt(*t) for t in clk_lines]
io = "physical/ref_tile_specs/smh/smh_tile_rp4c_pins.tcl"
(ROOT / io).write_text("\n".join(lines) + "\n")

longest = sorted((e for e in entries if not e.get("glue_root")), key=lambda e: -e["manhattan_um"])
spec.update(name="smh_tile_rp4c", outline={"w": W, "h": H}, io_tcl=io, children=children)
spec["job"].update(
    owner="Claude H-SM rp4 helper 0600", tag="rp4c",
    structural_change=("RP4b CTS gate smh_tile_rp4b-20261016-040329 measured 17/18 hard clock entries LONG (104-791 um "
                       "unbuffered one-pin wires, TT 39-1161 ps, slew 124-3682 ps): every clock port was on W at arbitrary y. "
                       "RP4c: entry pins at each child's actual LEF clock-pin projection on N/S/W/E faces; leaf1 = exact MX "
                       "mirror of leaf0; beat_t in the W column aligned with pte beat; lands beside their x stores; rows "
                       "aligned W/E; glue roots beside their sink groups. Same RTL / data edges. Outline 406.08 x 1529.28 "
                       f"(+95.04 um height). Longest entries: {longest[0]['port']} {longest[0]['manhattan_um']} um, "
                       f"{longest[2]['port']} {longest[2]['manhattan_um']} um (third)."))
(ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4c.json").write_text(json.dumps(spec, indent=1) + "\n")

out = ROOT / "results/arch/hbm_sm_repack_1015/rp4c_entries"
out.mkdir(exist_ok=True, parents=True)
win = {}
for face in "WE":
    ys = sorted(v[2] for p, v in pins.items() if (v[1] > 0) == (face == "E"))
    win[face] = {"data_pin_min_um": ys[0], "data_pin_max_um": ys[-1], "span_frac": round((ys[-1] - ys[0]) / H, 3)}
(out / "plan.json").write_text(json.dumps(dict(
    schema="opentallas.rp4c_entries.v1", outline={"w": W, "h": H}, geometry=st, children=children, clock_entries=entries,
    data_pin_windows=win, output_links_n=len(links), normal_edges_added=0, tile_height_delta_um=round(H - 1434.24, 2),
    sm_frame_note="16 tiles per SM row at 427.68 pitch unchanged (width 406.08); height 1529.28 + 21.6 + XC 216 = 1766.88 <= 1780",
    scope="Geometry/pin candidate. Actual CTS / trial GRT / route OPEN."), indent=2) + "\n")
notes = [(e["pin_um"][0] if e["pin_um"][0] < W / 2 else W - 60, e["pin_um"][1], e["port"].replace("clk_", "") + f" {e.get('manhattan_um', '')}")
         for e in entries]
draw(out / "floorplan.png", W, H, boxes, "RP4c: hard clock entries at child clock pins (port, um)", notes=notes)
print(json.dumps(dict(geometry=st, windows=win, entries=[(e["port"], e["face"], e.get("manhattan_um")) for e in entries])))
