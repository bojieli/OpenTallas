"""DIE-HBM-10: PHY_N C23 split traffic map (COORD ruling DIE-HBM-10 ASK 1: map first, with each group's clock pin and the
PG/bump contract).  Pure data from the plan + the generator; no build.
usage: mk_c23_map.py PLAN_JSON CA_JSON OUT_JSON"""
import json, sys
plan, caf, out = sys.argv[1:4]
P = json.load(open(plan)); T = P["partition_types"]["PHY_N"]
WIN = 265.6; NPC = 32; MACRO_W = 8500.032; PN_W = T["outline_um"][0]; OFF = round((PN_W - MACRO_W) / 2, 2)
G = 8.64
def snap(v): return round(round(v / G) * G, 2)
# per-PC boundary bits (hbm_phy_gen.py rc_pins): data in = row_row 19 + col_data 256 + col_strb 32 = 307;
# ctl in = row_v 1 + row_op 3 + row_bank 5 + col_v 1 + col_we 1 + col_bank 5 + col_col 5 = 21; out = rdata 256 + rvalid 1
DIN, CIN, DOUT, COUT = 307, 21, 256, 1
buses = {b["name"]: b for b in T["buses"]}
assert buses["L8_i"]["width"] == 8 * DIN and buses["L9_i"]["width"] == 8 * DIN
assert buses["L63_i"]["width"] == 16 * CIN and buses["L21_o"]["width"] == 8 * DOUT and buses["L114_o"]["width"] == 16 * COUT
groups = {
  "W": dict(pcs=list(range(0, 8)), hub="NW", data_in=["L8 (2456 = PC0-7 x 307)"], ctl_in=["L63[0:167] (PC0-7 x 21)"],
            data_out=["L21 (2048 = PC0-7 rdata)"], ctl_out=["L114[0:7] (PC0-7 rvalid)"],
            region="T060W (child of T059: W face, as L8/L21 today)"),
  "C": dict(pcs=list(range(8, 24)), hub="NW (PC8-15) + NE (PC16-23)",
            data_in=["L9 (PC8-15)", "L9m (PC16-23)"], ctl_in=["L63[168:335] (PC8-15)", "L63m[168:335] (PC16-23)"],
            data_out=["L22 (PC8-15 rdata)", "L22m (PC16-23 rdata)"], ctl_out=["L114[8:15]", "L114m[8:15]"],
            region="T060C (child of T057: centre column vsN6, as L9/L63/L114 today)"),
  "E": dict(pcs=list(range(24, 32)), hub="NE", data_in=["L8m (PC24-31)"], ctl_in=["L63m[0:167] (PC24-31)"],
            data_out=["L21m (PC24-31 rdata)"], ctl_out=["L114m[0:7]"],
            region="T060E (child of T061: E face, as L8m/L21m today)"),
}
# Slice macros on the 8.64 lattice: W = E = 246 x 8.64 = 2125.44 um (8 windows = 2124.8), C = 492 x 8.64 = 4250.88 um
# (16 windows = 4249.6); total 8501.76 um = gen_arch PHYW.  PHY_N 8804.16 um = 1019 units: W margin 17 units (146.88),
# E margin 18 units (155.52).  Cuts at 2272.32 / 6523.2 um; each slice sits wholly in its partition, pins keep the
# 265.6-um window pitch from the slice origin.
UNITS = {"W": 246, "C": 492, "E": 246}; MW, ME = 17 * G, 18 * G
cur = 0.0
for g, d in groups.items():
    lo, hi = d["pcs"][0], d["pcs"][-1] + 1
    sw = round(UNITS[g] * G, 2)
    px0 = cur; sx0 = px0 + (MW if g == "W" else 0.0)
    px1 = round(sx0 + sw + (ME if g == "E" else 0.0), 2); cur = px1
    mid = (hi - lo) // 2
    d.update(slice_macro=dict(width_um=sw, height_um=1177.2, windows=hi - lo, partition_origin_x_um=round(sx0 - px0, 2)),
             partition_x_um=[round(px0, 2), px1], partition_w_um=round(px1 - px0, 2),
             channels=[f"ch{c}" for c in range(lo // 2, hi // 2)],
             clock_pin=dict(pin="clk", slice_window=mid, pc=lo + mid, partition_x_um=round(sx0 - px0 + mid * WIN, 1),
                            face="S (core side)", tree=f"own region tree {d['region'].split()[0]}, inverter local form 12.16e"),
             reset_pin=dict(pin="rst_n", slice_window=mid, note="hb_ckgen por_hbm via the region's hbfd_rrl leaf (die reset contract 64 edges)"),
             bits_in=len(d["pcs"]) * (DIN + CIN), bits_out=len(d["pcs"]) * (DOUT + COUT),
             power_w=round(10.48 * len(d["pcs"]) / NPC, 2))
assert abs(cur - PN_W) < 1e-6, cur
ca = json.load(open(caf)); rows = {r["link"]: r for r in ca["direct_rows"]}
for g, k in (("W", "T059~T060W"), ("C", "T057~T060C"), ("E", "T060E~T061")):
    r = rows[k]; groups[g]["ca_link"] = dict(link=k, unshared_ps=r["unshared_ps"], depth=r["depth"], m_lo=r["m_lo"], m_hi=r["m_hi"],
                                             grade="UNCHECKED model (inverter tree; CLK-INV-CAL-1 pending)")
out_d = dict(
  schema="opentallas.hbm.phy_split_map.v1", event="C23 (planned, not built)", plan=plan,
  macro="ot_hbm3e_phy_rc_e8p5 (8500.032 x 1177.2 um, ASSUMED licensed-PHY abstract, 32 PCs, PC p pins in window p of 265.6 um)",
  as_built_binding="physical/die_plan/hbm/bind/asbuilt_map.json: PHY PC p = ctl_NW_p{p}; p 0-15 -> NW_hub ctl_p00-15, p 16-31 -> NE_hub ctl_p00-15",
  bus_bits=dict(per_pc_data_in=DIN, per_pc_ctl_in=CIN, per_pc_out=DOUT + COUT,
                check="L8 = L9 = 8 x 307 = 2456; L21 = L22 = 8 x 256 = 2048; L63 = 16 x 21 = 336; L114 = 16 (CHECKED vs plan buses)"),
  groups=groups,
  traffic_rule=("No signal crosses a group cut: each PC's boundary pins (row/col/data/strb in, rdata/rvalid out) sit in its own window "
                "and connect only to its own controller (ot_hbm_svc_pc_ctrl_leaf); groups are whole HBM3 channels (PC pairs). "
                "The only shared macro pins today are clk and rst_n (window 16), replaced by one clk/rst_n per slice."),
  plan_delta=["PHY_N -> PHY_NW / PHY_NC / PHY_NE abutting hard partitions, cuts at x = 2272.32 / 6523.2 um (8.64 grid), each holding one slice macro",
              "L63 / L63m and L114 / L114m split 8|8 PCs: the W (E) half follows the L8/L21 (L8m/L21m) path T055->T059->T060W "
              "(T056->T061->T060E); the C half keeps the vsN6 path",
              "L22 / L22m leave PHY_NC via T060C->T057 (today they leave from the W/E side): no new region pair, bits only",
              "bus bit order fixed by PC (composer): the bundles carry whole PCs"],
  pg_bump=dict(
    core_grid="opentallas.core_bumps.v1 150-um VDD/VSS checkerboard (pg_bumps.json) skips the PHY io windows: unchanged",
    phy_domain="each slice keeps the PHY domain's own 45-um micro-bump rows under its PC windows (package side, blackbox to the core flow); "
               "cuts fall on channel-pair boundaries, so no channel's DQ/CA bumps straddle a cut (ASSUMED: the IP's bump map is per channel)",
    straps="each slice macro keeps the M4 VDD/VSS straps (OBS M1-M4) over its own width; parent M5 stripes via-in per slice (same rule as today)",
    power="10.48 W per stack (1.2 TB/s x 0.8 pJ/bit + 2.8 W idle, hbm_b2_power.py, ASSUMED basis) split by PC count: W 2.62 / C 5.24 / E 2.62 W"),
  generator_variant=("opt-in hbm_phy_gen.py --variant rc_slice --pcs LO-HI (default rc unchanged, byte-identical): same per-PC pins and "
                     "windows, footprint = the group's windows snapped up to 8.64 (246 / 492 units), clk/rst_n in the group's middle window; ROOT-MERGE (shared tool)"),
  assumptions=["the licensed HBM3E PHY supports per-channel-group (4-channel) clocking with one clock input per group; "
               "stack-global functions (IEEE1500 test port, temperature, global reset) live in the C slice",
               "region insertion scaled from the equal-thirds split by the half-width change (mk_feed_c23.py)"],
)
json.dump(out_d, open(out, "w"), indent=1)
for g, d in groups.items():
    print(g, d["pcs"][0], d["pcs"][-1], d["partition_x_um"], d["partition_w_um"], d["slice_macro"], d["clock_pin"], d["bits_in"], d["bits_out"], d["power_w"], d["ca_link"])
