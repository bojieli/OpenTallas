#!/usr/bin/env python3
"""DIE-HEAD-47 plan event l47t = l47k + hd_st_turn local reset copy (COORD 03:3x, GEOM-87/86 hd_st_turn item 1).

GEOM-87 (03:24): r2r 1368.74 x2 = u_cland_rst_d_i (1046,448; d_i side, depth-5 copy of rst_rl_3) -> via
cland_start_raw -> u_cland_fstart_d_o (355,1126; the d_o FSTART exporter at the N face).  Fix in the type's own
form (clock_landings._local_resets, DIE-HEAD-38 R1): a kept ot_dp_rrelay u_cland_lrst_geo_30 at the d_o exporter,
d = rst_rl_45 (raw wavefront relay at (350.1,1028.2), depth 4) -> depth 5 = the depth of cland_reset_d_i, so the
release edge is unchanged (same-cycle copy); u_cland_fstart_d_o.rst_raw_n takes it.  u_cland_fstart_u_o keeps
cland_start_raw.  Plan clock.landing_local_resets gets the matching entry (the kit places the copy at xy_um).
  make_l47t.py SRC_DIR(head_source_l47k) OUT_DIR
"""
import json, re, shutil, sys
from pathlib import Path

src, out = map(Path, sys.argv[1:3])
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
pf = out / "source_plan.json"; plan = json.loads(pf.read_text())
lr = plan["partition_types"]["hd_st_turn"]["clock"]["landing_local_resets"]
assert "geo_30" not in {r["name"] for r in lr} and not any("u_cland_fstart_d_o" in r["consumers"] for r in lr)
lr.append(dict(name="geo_30", raw="rst_rl_45", xy_um=[355.0, 1120.0], consumers=["u_cland_fstart_d_o"]))
pf.write_text(json.dumps(plan, indent=1) + "\n")
vf = out / "ot_s81hd_st_turn.sv"; v = vf.read_text()
old = "ot_dp_landing_relay u_cland_fstart_d_o (.clk(clk), .rst_raw_n(cland_start_raw),"
assert v.count(old) == 1 and v.count("assign cland_start_raw = cland_reset_d_i;") == 1
assert re.search(r"ot_dp_rrelay u_rrl_45 \(\.clk\(clk\), \.d\(rst_rl_44\), \.q\(rst_rl_45\)\);  // raw wire tap None depth 4", v)
assert re.search(r"ot_dp_rrelay u_rrl_3 \(\.clk\(clk\), \.d\(rst_rl_2\), \.q\(rst_rl_3\)\);  // raw pad tap \d+ depth 4", v)
v = v.replace(old, "ot_dp_landing_relay u_cland_fstart_d_o (.clk(clk), .rst_raw_n(cland_lrst_geo_30),")
# same text/order as clock_landings._local_resets emits for the appended plan entry (byte-checked by head_rekit_current)
anchor = ("    (* keep = \"true\" *) ot_dp_rrelay u_cland_lrst_origin_geo (.clk(clk), .d(rst_rl_92), .q(cland_lrst_origin_geo));"
          "  // local same-cycle reset copy (depth 5)\n")
assert v.count(anchor) == 1
v = v.replace(anchor, anchor + "    wire cland_lrst_geo_30;\n    (* keep = \"true\" *) ot_dp_rrelay u_cland_lrst_geo_30 (.clk(clk), "
                      ".d(rst_rl_45), .q(cland_lrst_geo_30));  // local same-cycle reset copy (depth 5)\n")
vf.write_text(v)
print("l47t: hd_st_turn geo_30 (rst_rl_45 -> u_cland_fstart_d_o) added")
