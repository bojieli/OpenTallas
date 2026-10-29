#!/usr/bin/env python3
"""DIE-HEAD-31 hd_tile hk5m kit: head_tile_source7_kit.py on the hk5m plan + the class-A locality kit patches.
usage: hk5m_tile_kit.py ROOT HK5L_SRC HK5M_PLAN OUT        (OUT/src = source copy, OUT/gen = base kit, OUT/v1, OUT/v2)
Patches (0 cycles, 0 flops):
 * u_cland_rst_i.d rst_rl_11 -> rst_rl_39: both are depth-3 plain raw relay chains from rst_root_n
   (root->rl_9->rl_10->rl_11 vs root->rl_27->rl_34->rl_39; rl_10/rl_34 are export pairs whose q is the relay), so the
   cland reset is released in the SAME cycle; rl_39 sits at (505.4,730.1) next to the band instead of the tile centre.
 * FIRM relay targets of the CA control cluster from the hk5 band pins (static pre-hk5 rows replaced) and the core
   status launchers goo_q/xvo_q/o_rv re-anchored towards the E band bottom (status bits 512..564 now at y 708-737).
V1 = PLACE_DENSITY .35 (die-head-29/30 V1 knob); V2 = 40 % channel blockage y 699.9-734.4 (die-head-29/30 V2 knob)."""
import json, shutil, subprocess, sys
from pathlib import Path
root, src, plan, out = map(Path, sys.argv[1:5])
out.mkdir(parents=True)
s7 = out / "src/source7"; s7.mkdir(parents=True)
for f in (src / "source7").iterdir():
    if f.name != "source_plan.json":
        shutil.copy2(f, s7 / f.name)
shutil.copy2(plan, s7 / "source_plan.json")
(out / "src/input4").symlink_to((src / "input4").resolve())
sys.path[:0] = [str(root / "tools/s81_head"), str(root / "tools/die_plan")]
import head_tile_source7_kit as H
kit = Path(H.build(out / "src", out / "gen"))
OLD = "    ot_dp_rrelay u_cland_rst_i (.clk(clk), .d(rst_rl_11), .q(cland_reset_i));\n"
NEW = ("    // DIE-HEAD-31 hk5m: same depth-3 raw chain released in the same cycle, relay next to the band (rl_39 @505,730)\n"
       "    ot_dp_rrelay u_cland_rst_i (.clk(clk), .d(rst_rl_39), .q(cland_reset_i));\n")
wr = [p for p in (out / "gen/_rtl").glob("ot_s81hd_tile*.sv")]
assert len(wr) == 1, wr
for p in (wr[0], kit / "rtl" / wr[0].name):
    t = p.read_text()
    assert t.count(OLD) == 1 and "u_rrl_39 (.clk(clk), .d(rst_rl_34), .q(rst_rl_39));  // raw wire tap None depth 3" in t
    assert "u_rrl_34 (.clk(clk), .d(rst_rl_27)" in t and "u_rrl_27 (.clk(clk), .d(rst_root_n)" in t
    p.write_text(t.replace(OLD, NEW))
# macro-free sites (eA0-3 + eB 216-501 x 734.4-1019.5 excluded; channel y 699.84-734.4 free), all hops <= 397 um
ANCH = {"u_cland_origin/sf$_DFF_N_": (518.4, 862.9), "u_cland_origin/s0$_SDFF_PN0_": (518.4, 862.9),
        "u_cland_origin/s1$_SDFF_PN0_": (505, 830), "u_cland_origin/g_export.g_copy\\[0\\].u_copy/q$_SDFF_PN0_": (620, 866),
        "u_cland_fstart_o/q$_SDFF_PN0_": (700, 867), "u_cland_origin/s2$_SDFF_PN0_": (200, 830),
        "u_cland_origin/pd$_SDFF_PN0_": (200, 830),
        "u_cland_agg_1/fault_o$_SDFF_PN0_": (190, 800), "u_cland_agg_1/ready_o$_SDFF_PN0_": (190, 800),
        "u_cland_agg_2/fault_o$_SDFF_PN0_": (520, 862), "u_cland_agg_2/ready_o$_SDFF_PN0_": (520, 862),
        "u_cland_rst_i/q$_DFF_P_": (450, 720),
        "u_core.goo_q$_DFF_PN0_": (375, 717), "u_core.xvo_q$_DFF_PN0_": (375, 717), "u_core.o_rv$_DFF_PN0_": (375, 717)}
tsv = kit / "head_tile_relay_targets.tsv"
rows, seen = [], set()
for l in tsv.read_text().splitlines():
    n = l.split("\t")[0]
    if n in ANCH:
        seen.add(n); x, y = ANCH[n]; l = f"{n}\t{x}\t{y}"
    rows.append(l)
for n in ANCH:
    if n not in seen:
        rows.append(f"{n}\t{ANCH[n][0]}\t{ANCH[n][1]}"); print("added target", n)
tsv.write_text("\n".join(rows) + "\n")
blk = (kit.parent.parent / "../../die-head-30/hk5l/var_v2/hd_tile/face_flops.tcl")
for v in ("v1", "v2"):
    d = out / v; shutil.copytree(out / "gen", d, symlinks=True)
    k = d / kit.name
    if v == "v1":
        c = (k / "config.mk").read_text(); assert c.count("export PLACE_DENSITY = 0.5\n") == 1
        (k / "config.mk").write_text(c.replace("export PLACE_DENSITY = 0.5\n", "export PLACE_DENSITY = 0.35\n"))
    else:
        f = k / "face_flops.tcl"
        f.write_text(f.read_text() + """
# DIE-HEAD-31 hk5m V2 (= die-head-29/30 V2 knob, 0 cycles, kit-only): 40 % max-density partial blockage on the 34.56-um
# channel between the eA2/eA3 tops (y 699.852) and the eB bottom (y 734.412), x 4.32..704.16.
set dh29_blk [ord::get_db_block]
set dh29_u [[ord::get_db_tech] getDbUnitsPerMicron]
set dh29_b [odb::dbBlockage_create $dh29_blk [expr {int(4.32*$dh29_u)}] [expr {int(699.852*$dh29_u)}] [expr {int(704.16*$dh29_u)}] [expr {int(734.412*$dh29_u)}]]
$dh29_b setMaxDensity 40.0
puts "DH29_CHANNEL_BLOCKAGE max_density [$dh29_b getMaxDensity]"
""")
print(json.dumps(dict(kit=str(kit), v1=str(out / "v1" / kit.name), v2=str(out / "v2" / kit.name))))
