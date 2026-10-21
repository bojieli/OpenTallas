#!/usr/bin/env python3
"""RP4e (H-SM 1315, 2026-10-16): the W / E pass-through spread over >= 1,000 um of each face, on a W strip widened by DW.

RP4d gate smh_tile_rp4d-20261016-102656 (E4) was stopped at trial GRT extra iteration 17/30 after ~1 h, the RP4c
symptom again: 3,721 W / 3,713 E pins (bin/bout 2,069 + rin/rout 1,636) packed into y 550-979 (bin 10.4 pins/um), a
red pin-flop strip at x < 15 um, post-CTS reg->reg -391.7 ps.  The pass-through has to cross the tile in the 615 um
middle band (the two x stores and the BD / column groups block M2-M7 across the full width outside it), so a spread
pin plan needs VERTICAL distribution strips on both faces: ~1,850 bits per direction / 0.60 / 64.2 vertical tracks
per um (M3 + M5 + M7) = 48 um.  The E strip (right edge of the leaf columns -> E face) is ~56 um already; the W strip
(face -> x stores / BD at 25.92) was 25.92 um.  RP4e (H-DIE d4c grant: +24 um per SM, no die growth; +48 with the HC
re-grant):
  * outline W + DW; every child + DW in x EXCEPT the W transport column (lands / rows / beat_t at 56.16, which sit in
    the middle band and keep their < 60 um clock entries), so the W strip outside the middle band becomes 25.92 + DW;
  * rin/bin (W) and rout/bout (E) spread evenly, order kept, over y [Y0, Y1] (>= 1,000 um, centred on the middle
    band); rX[i] and rY[i] at the SAME y on W and E (tile abutment), clear of every W/E clock pin by >= 1.08 um;
  * N / S pins (leaf straps, gin/gout, clk_hard) + DW in x (they follow the shifted leaves); W / E clock pins keep y.
Same RTL, leaves, children and cycle counts (no bench / schedule change).
    rp4e_successor.py [DW]      (default 24.0; a multiple of the 4.32 child lattice is not needed for the outline)
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

DWW = float(sys.argv[1]) if len(sys.argv) > 1 else 25.92   # W strip gain (leaves + E column shift right)
DWE = float(sys.argv[2]) if len(sys.argv) > 2 else 25.92   # E strip gain (E transport column shifts DWW + DWE)
DWW = round(round(DWW / 4.32) * 4.32, 2); DWE = round(round(DWE / 4.32) * 4.32, 2)   # child lattice
DW = round(DWW + DWE, 2)
W0, H = 406.08, 1529.28
W = round(W0 + DW, 2)
TAG = "rp4e"
Y0, Y1 = 249.6, 1281.6                           # pass-through window (1,032 um), centred on the middle band
M4 = lambda k: round(0.012 + 0.048 * k, 3)      # noqa: E731
k_of = lambda v: round((v - 0.012) / 0.048)     # noqa: E731

spec = json.loads((ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4d.json").read_text())
KEEP = {"u.u_ptw.u_land_s", "u.u_ptw.u_row1", "u.u_ptw.u_beat_t", "u.u_ptw.u_row0", "u.u_ptw.u_land_n"}
SIZE, LEF, boxes, ent = {}, {}, [], {}
for c in spec["children"]:
    v = c["view"]
    if v not in LEF:
        LEF[v] = parse_lef((ROOT / v / (Path(v).name + ".lef")).read_text())
        SIZE[v] = (LEF[v]["W"], LEF[v]["H"])
    if c["inst"] not in KEEP:
        c["at"] = [round(c["at"][0] + DWW + (DWE if "u_pte" in c["inst"] else 0.0), 2), c["at"][1]]
    m = Path(v).name
    boxes.append(("row" if "row" in m else m.replace("ot_hbm_accel_smh_", "").replace("ot_smh_tr_group_", ""),
                  c["inst"], c["at"][0], c["at"][1], *SIZE[v]))
    r = LEF[v]["pins"].get("clk", {}).get("rects")
    if r:
        cx = (r[0][1] + r[0][3]) / 2
        ent[c["inst"]] = round(min(c["at"][0] + cx, W - (c["at"][0] + cx)), 2)
st = stats(W, H, boxes)
assert not st["overlaps"] and not st["slivers_um"], st
# W strip outside the middle band = the leftmost child x among the shifted (non-KEEP) children
wstrip = min(c["at"][0] for c in spec["children"] if c["inst"] not in KEEP)
estrip = W - max(c["at"][0] + SIZE[c["view"]][0] for c in spec["children"] if "u_pte" not in c["inst"])   # outside the middle band

pat = re.compile(r"place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([^ ]+) ([^}]+)\}")
pins = []
for ln in (ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4d_pins.tcl").read_text().splitlines():
    mm = pat.search(ln)
    if mm:
        pins.append([mm[1], mm[2], float(mm[3]), float(mm[4])])
base = lambda p: p.split("[")[0]                 # noqa: E731
idx = lambda p: int(p.split("[")[1][:-1]) if "[" in p else 0  # noqa: E731
clk_y = [p[3] for p in pins if p[2] in (0.0, W0) and base(p[0]).startswith("clk")]
# one y list for the W face order (rin then bin as in RP4d, by index), mirrored on E
wlist = sorted([p for p in pins if p[2] == 0.0 and base(p[0]) in ("rin", "bin")], key=lambda p: p[3])
n = len(wlist)
tracks = [k for k in range(k_of(Y0), k_of(Y1) + 1) if all(abs(M4(k) - y) >= 1.08 for y in clk_y)]
assert len(tracks) >= n, (len(tracks), n)
sel = [tracks[round(i * (len(tracks) - 1) / (n - 1))] for i in range(n)]
assert len(set(sel)) == n
newy = {p[0]: M4(k) for p, k in zip(wlist, sel)}
mirror = {"rin": "rout", "bin": "bout"}
for p in pins:
    b = base(p[0])
    if p[2] == 0.0 and b in mirror:
        p[3] = newy[p[0]]
    elif p[2] == W0 and b in ("rout", "bout"):
        twin = {"rout": "rin", "bout": "bin"}[b] + p[0][len(b):]
        p[2], p[3] = W, newy[twin]
    elif p[2] == W0:
        p[2] = W
    elif p[3] in (0.0, H):
        p[2] = round(p[2] + DWW, 3)
pitch = (Y1 - Y0) / n


def fmt(port, layer, x, y):
    size = "{0.192 0.024}" if layer == "M4" else "{0.024 0.192}"
    return f"place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {size} -force_to_die_boundary"


io = f"physical/ref_tile_specs/smh/smh_tile_{TAG}_pins.tcl"
(ROOT / io).write_text("\n".join(
    [f"# generated by tools/hbm_sm_repack_1015/rp4e_successor.py {DW}: RP4d pin plan, rin/bin + rout/bout spread over "
     f"y {Y0}-{Y1} (W = E y), N/S + {DW}, outline {W} x {H}"] + [fmt(*p) for p in pins]) + "\n")
spec["outline"] = {"w": W, "h": H}
spec["job"].update(
    owner="Claude H-SM 1315", tag=TAG,
    structural_change=(
        f"RP4d gate (E4 smh_tile_rp4d-20261016-102656) stopped at trial GRT extra 17/30 (~1 h): 3,721 W / 3,713 E "
        "pass-through pins in y 550-979 (bin 10.4 pins/um), red W pin-flop strip, post-CTS reg->reg -391.7. "
        f"{TAG}: outline +{DW} um (H-DIE d4c grant), all children except the W transport column +{DW} (W strip outside "
        f"the middle band 25.92 -> {wstrip}, E strip {round(estrip, 2)}), rin/bin and rout/bout spread over y {Y0}-{Y1} "
        f"({n} bits per face, {round(n / (Y1 - Y0), 2)} pins/um, W y == E y), N/S pins +{DW}. Same RTL / children / cycles."))
spec.update(name=f"smh_tile_{TAG}", io_tcl=io)
(ROOT / f"physical/ref_tile_specs/smh/smh_tile_{TAG}.json").write_text(json.dumps(spec, indent=1) + "\n")
out = ROOT / f"results/arch/hbm_sm_repack_1015/{TAG}_refloor"
out.mkdir(exist_ok=True, parents=True)
(out / "plan.json").write_text(json.dumps(dict(
    schema="opentallas.rp4e_refloor.v1", dw_um=DW, outline={"w": W, "h": H}, geometry=st, w_strip_um=wstrip,
    e_strip_um=round(estrip, 2), passthrough_window_y=[Y0, Y1], bits_per_face=n, pin_pitch_um=round(pitch, 3),
    clock_entry_um=ent, scope="Geometry/pin candidate. Actual CTS / trial GRT / route OPEN."), indent=2) + "\n")
draw(out / "floorplan.png", W, H, boxes, f"{TAG}: W strip {wstrip} um, pass-through y {Y0}-{Y1}", notes=[])
print(json.dumps(dict(W=W, w_strip=wstrip, e_strip=round(estrip, 2), bits=n, pitch=round(pitch, 3),
                      max_entry=max(ent.values()), entries_over_60=[k for k, v in ent.items() if v >= 60.0])))
