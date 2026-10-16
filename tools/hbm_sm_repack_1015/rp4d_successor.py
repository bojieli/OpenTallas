#!/usr/bin/env python3
"""RP4d: structural re-floorplan of RP4c from its gate evidence (smh_tile_rp4c-20261016-061544, killed at trial GRT
extra iteration 19/30 after 3.5 h; evidence /home/ubuntu/artifacts/hsm-rp4-0600/rp4c).

Measured RP4c problems and the RP4d answer (same leaves, same children, same cycle counts):
  1. W pin strip.  Every W-column transport child (lands, rows, beat_t) sat at x 25.92, so the 3,705 rin/bin pin flops
     plus their recipe-3 FIRM pin hold stages (HB4 + BUF per input), the 3 clk_pin trees (3,705 sinks) and the vertical
     bin_l feeds to both lands (2 x 2,069) all had to share a 25.92 um strip between the W face and the children.  RP4d
     moves those five children east to x 56.16 (strip 2.17x; the entry wire to each child clock pin stays < 60 um, the
     clock_entries LONG limit), moves the lands toward the centre of their x store's bk1 row (land centre 133.9 -> 164.2 um, bk1 centre 176.7), and moves each row group's
     `first` bus (rl1) toward its x store's rl1 pins.  Pin flop columns 6 -> 10 use the wider strip.
  2. Hard-glue path.  Leaf 1's xs_* straps entered on the N face and crossed the tile over clk_region[0] -> [1] -> [2]
     (pc.log reg->macro -309.2 ps at u.g_lf[1].u_lh.u_xs/xs_g1[4], reg->reg -308.1 ps at g_strap[1].u_sr).  RP4d enters
     leaf 1's 26 strap bits on the S face in the free x 138-164 channel straight below leaf 1's x store and runs all five
     strap stages on clk_region[2] (rtl ot_hbm_smh_rp4_strap: one leaf root per leaf).  Same five stages = same static
     cycle count; no bench / schedule change.
W / E pass-through pins stay at the y of the hard row / beat bits (rin y == rout y for abutment): the two x stores
(302.4 um wide) and the block-dot / column groups block every horizontal layer the tile owns (M2-M7) across the full
width outside the 615 um middle band, M8 is not granted to SM tiles (HANDOFF: "6.21 mm2/SM needs M8/M9 (not granted)"),
so a >= 1,000 um W / E pin spread is not reachable without re-shaping the leaves or an M8 grant (owner / H-DIE question).
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
XW = 56.16          # new W-column x (13 x 4.32 child lattice); RP4c 25.92
M4 = lambda k: round(0.012 + 0.048 * k, 3)  # noqa: E731
k_of = lambda v: round((v - 0.012) / 0.048)  # noqa: E731

spec = json.loads((ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4c.json").read_text())
MOVE = ["u.u_ptw.u_land_s", "u.u_ptw.u_row1", "u.u_ptw.u_beat_t", "u.u_ptw.u_row0", "u.u_ptw.u_land_n"]
SIZE, LEF = {}, {}
boxes = []
for c in spec["children"]:
    v = c["view"]
    if v not in LEF:
        LEF[v] = parse_lef((ROOT / v / (Path(v).name + ".lef")).read_text())
        SIZE[v] = (LEF[v]["W"], LEF[v]["H"])
    if c["inst"] in MOVE:
        assert abs(c["at"][0] - 25.92) < 1e-6, c
        c["at"] = [XW, c["at"][1]]
    m = Path(v).name
    boxes.append(("row" if "row" in m else m.replace("ot_hbm_accel_smh_", "").replace("ot_smh_tr_group_", ""),
                  c["inst"], c["at"][0], c["at"][1], *SIZE[v]))
st = stats(W, H, boxes)
assert not st["overlaps"] and not st["slivers_um"], st

# clock entry length to each moved child's clock pin (W face, same y as RP4c)
ent = {}
for c in spec["children"]:
    if c["inst"] in MOVE:
        v = c["view"]
        r = LEF[v]["pins"]["clk"]["rects"][0]
        cx = (r[1] + r[3]) / 2
        ent[c["inst"]] = round(c["at"][0] + cx, 2)
        assert ent[c["inst"]] < 60.0, (c["inst"], ent[c["inst"]])

# ---- pins: RP4c plan, leaf-1 straps (j = 1 slices) moved to the S face
pat = re.compile(r"place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([^ ]+) ([^}]+)\}")
lines_in = (ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4c_pins.tcl").read_text().splitlines()
J1 = [f"xs_a1[{i}]" for i in range(9, 18)] + [f"xs_a2[{i}]" for i in range(7, 14)] + \
     [f"xs_g1[{i}]" for i in range(5, 10)] + [f"xs_g2[{i}]" for i in range(5, 10)]
used_s = set()
pins = []
for ln in lines_in:
    mm = pat.search(ln)
    if not mm:
        continue
    port, layer, x, y = mm[1], mm[2], float(mm[3]), float(mm[4])
    if y == 0.0 and layer == "M5":
        used_s.add(k_of(x))
    pins.append([port, layer, x, y])
# S-face channel between leaf-1 block-dot (x <= 138.24) and leaf-1 column h0 (x >= 164.16): 26 bits at 0.48 um
x0 = 141.0
new = {}
k = k_of(x0)
for p in J1:
    while any(abs(k - u) <= 3 for u in used_s):
        k += 1
    new[p] = M4(k)
    used_s.add(k)
    k += 10
assert max(new.values()) < 164.16 - 1.0 and min(new.values()) > 138.24 + 1.0, new
for p in pins:
    if p[0] in new:
        assert p[3] == H, p
        p[2], p[3] = new[p[0]], 0.0


def fmt(port, layer, x, y):
    size = "{0.192 0.024}" if layer == "M4" else "{0.024 0.192}"
    return f"place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {size} -force_to_die_boundary"


io = "physical/ref_tile_specs/smh/smh_tile_rp4d_pins.tcl"
(ROOT / io).write_text("\n".join(
    ["# generated by tools/hbm_sm_repack_1015/rp4d_successor.py: RP4c pin plan; leaf-1 xs_* straps (j = 1) on the S face",
     "# in the x 138-164 channel below leaf 1's x store (all strap stages on clk_region[2])"] +
    [fmt(*p) for p in pins]) + "\n")

spec["pins"]["S"] = sorted(set(spec["pins"]["S"]) | {"xs_a1", "xs_g1", "xs_a2", "xs_g2"})
spec["io_flop_at_pins"]["cols"] = 10
spec["job"].update(
    owner="Claude H-SM rp4d helper 0945", tag="rp4d",
    structural_change=(
        "RP4c gate smh_tile_rp4c-20261016-061544 killed at trial GRT extra 19/30 (3.5 h): 3,705 W pin flops + "
        "recipe-3 pin hold stages + 3 clk_pin trees + 2 x 2,069 bin_l feeds to the lands in a 25.92 um W strip; "
        "pc.log reg->macro -309.2 ps (leaf1 u_xs/xs_g1) and reg->reg -308.1 ps (g_strap[1]) because leaf1's straps "
        "entered N and crossed the tile over clk_region[0/1/2]. RP4d: W-column lands/rows/beat_t x 25.92 -> 56.16 "
        f"(strip 2.17x, entries {min(ent.values())}-{max(ent.values())} um < 60), lands nearer the x-store bk1 centre, "
        "pin flop columns 6 -> 10; leaf1 xs_* straps on the S face (x 141-158 channel under leaf1's x store), all 5 "
        "strap stages on the leaf's own regional root (same cycle count). W/E pass-through y unchanged (abutment)."))
spec["job"]["benches"] = spec["job"].get("benches", [])
spec.update(name="smh_tile_rp4d", io_tcl=io)
(ROOT / "physical/ref_tile_specs/smh/smh_tile_rp4d.json").write_text(json.dumps(spec, indent=1) + "\n")

out = ROOT / "results/arch/hbm_sm_repack_1015/rp4d_refloor"
out.mkdir(exist_ok=True, parents=True)
(out / "plan.json").write_text(json.dumps(dict(
    schema="opentallas.rp4d_refloor.v1", outline={"w": W, "h": H}, geometry=st, moved=MOVE, w_column_x=XW,
    w_strip_um={"rp4c": 25.92, "rp4d": XW}, entry_wire_um=ent, leaf1_strap_pins_S=new,
    scope="Geometry/pin candidate. Actual CTS / trial GRT / route OPEN."), indent=2) + "\n")
draw(out / "floorplan.png", W, H, boxes, "RP4d: W strip 56 um, leaf-1 straps on S",
     notes=[(new["xs_a1[9]"], 8.0, "xs1 straps")])
print(json.dumps(dict(geometry=st, entries=ent, s_pins=[min(new.values()), max(new.values())])))
