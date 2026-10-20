#!/usr/bin/env python3
"""SVC4 (LEAD2-S81, 10-19): attw as a LANDED PARENT (landed-regions-standard-1018).

    python3 tools/s81_dv/svc_rs/mk_attw_lp.py [STD_AREA_UM2] [HG_W HG_H]
        -> tools/landed_parent/specs/dsdv_svc_attw_f.json      (lp.py spec; then lp.py gen it)
           tools/ref_tile/specs_s81dv_svc_lp/dsdv_svc_attw_f_lp.json  (ref_tile kit spec of the landed top)

Flat parent rtl/dsrom_sys/s81_dv/svc_rs/attw/dsdv_svc_attw_f.sv = u_c (dsdv_svc_rs_attw TEXT 1: the attention share with
the engine tiles exported) + u_t0..u_t3 (ot_hdc_v41x_attn_tile_s, -DOT_ATTN_HGRP_HARD: 4 hard s81svc_attn_hgrp groups
each).  Regions: c = u_c (centre column), t0..t3 = one per engine tile (one column of 4 head groups each).  Every tile
bundle (1,618 b in, 529 b out) is LANDED both ways: +3 edges each = TLX 6 (engine tag line re-schedule; the lockstep
reference is the flat parent with TLX = TXD = 6).

Floorplan (origin SW, 43.2 lattice; mk_attw_spec.py's W/E macro columns replaced by ONE centre column so region c is
compact and no landed crossing is longer than ~1 mm):
    | t0 | t1 |  c: big SRAM column (landing 12 + p store 4 + staging 16) | small SRAM column (38) | std  | t2 | t3 |
  tile t column: 4 head groups (g = row) of HG_W x HG_H, channel 86.4 between groups and columns.
  attw ports on N / S inside the c column (from the svc_rs slice above / below), clocks ck_c (S centre), ck_t<k>
  (S, under tile column k).  Defines: no SVCQ_ENG_FG3 (production engine FPL4 / FML6 / TILE_S 1),
  OT_ATTN_HGRP_HARD, OT_SVC_LAND_SRAM, OT_SVC_ATT_SRAM, OT_SVC_ATT_PINREG.
"""
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = float(sys.argv[1]) if len(sys.argv) > 1 else 190000.0          # attw minus tiles (census attwnotileg) + landing rings
HGW = float(sys.argv[2]) if len(sys.argv) > 2 else 388.8
HGH = float(sys.argv[3]) if len(sys.argv) > 3 else 388.8
G = 43.2
BW_, BH = 172.8, 41.04          # ot_sram_1r1w_256x256_m2_r2c2
SW, SH = 51.408, 20.79          # ot_sram_1r1w_32x128_m1
CH = 2 * G
r3 = lambda v: round(v, 3)
up = lambda v: round(math.ceil(v / G - 1e-9) * G, 3)
D = "rtl/dsrom_sys/s81_dv/svc_rs"
V = "rtl/hdc/v41x"
SRC = [f"{V}/ot_hdc_v41x_attn_hgrp_s81.sv", f"{V}/ot_hdc_v41x_attn_tile_s.sv", f"{V}/ot_hdc_v41x_attn_s.sv",
       f"{V}/ot_hdc_v41x_kreg.sv", f"{V}/ot_hdc_v41x_attn_tile_lat.sv", f"{V}/ot_hdc_v41x_attn_tile.sv",
       f"{V}/ot_hdc_v41x_attn.sv", f"{V}/ot_hdc_v41x_attn_staging.sv",
       "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
       "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v",
       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fp32_f12.sv",
       f"{V}/ot_dsrom_su_add6.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv",
       "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
       f"{D}/dsdv_svc_att.sv", f"{D}/dsdv_svc_rs_glue.sv"]
DEFS = ["OT_ATTN_HGRP_HARD", "OT_SVC_LAND_SRAM", "OT_SVC_ATT_SRAM", "OT_SVC_ATT_PINREG"]
PAR = dict(AMUT=0, DIE_ID=0, ST=0, SRAM_MACRO=1, ROOT=0, PMEM=1)

# ------------------------------------------------------------------ geometry
colh = 4 * HGH + 3 * CH
H = up(2 * CH + colh)
y0 = up((H - colh) / 2)
big_n, small_n = 12 + 4 + 16, 12 + 5 + 4 + 17
CW = up(G + BW_ + G + SW + G + max(A / 0.5 / (H - 2 * G), 4 * G) + G)   # c column: macros + std cells at ~50 %
xt = [CH, CH + HGW + CH]
xc = r3(xt[1] + HGW + CH)
xt = [r3(v) for v in xt + [xc + CW + CH, xc + CW + CH + HGW + CH]]
W = up(xt[3] + HGW + CH)
cen_y = r3(H / 2)
ms = []
def stack(view, w, h, x, y, insts):
    for i, n in enumerate(insts):
        ms.append({"view": f"physical/asap7_memory_macros/{view}", "inst": n, "count": 1,
                   "at": [r3(x), r3(y + i * h)], "orient": "R0" if i % 2 == 0 else "MX"})
stage = [f"*u_stage{s}.g_macro.g_lane?{l}?.g_slice?{k}?.g_256.u_mem" for s in (0, 1) for l in range(4) for k in range(2)]
land = [f"*u_core.g_land?{c}?.g_b?{b}?.u_mem" for b in range(4) for c in range(3)]
pmem = [f"*u_core.g_pmem.g_bank?{b}?.g_half?{h}?.u_mem" for b in range(2) for h in range(2)]
wq = [f"*u_core.g_wqh?{c}?.g_p?{p}?.g_m.u_wqm.g_m?{k}?.u_m" for c in (0, 2) for p in (0, 1) for k in range(3)]
sw = [f"*u_core.u_swm.g_m?{k}?.u_m" for k in range(5)]
qm = [f"*u_core.u_qmm.g_m?{k}?.u_m" for k in range(4)]
pv = [f"*u_core.g_pvq.u_pvm.g_m?{k}?.u_m" for k in range(17)]
bx = xc + G
by = up((H - big_n * BH) / 2)
stack("ot_sram_1r1w_256x256_m2_r2c2", BW_, BH, bx, by, land + pmem + stage)
sx = bx + BW_ + G
sy = up((H - small_n * SH) / 2)
stack("ot_sram_1r1w_32x128_m1", SW, SH, sx, sy, wq + sw + qm + pv)
HG_VIEW = "physical/ref_tile/s81svc_attn_hgrp/views/ot_hdc_v41x_attn_hgrp_s81"
ch = [{"view": HG_VIEW, "inst": f"u_t{t}.g_g?{g}?.u_g", "count": 1, "at": [r3(xt[t]), r3(y0 + g * (HGH + CH))]}
      for t in range(4) for g in range(4)]
regions = [{"name": "c", "insts": ["u_c"], "centre": [r3(xc + CW / 2), cen_y]}] + \
          [{"name": f"t{t}", "insts": [f"u_t{t}"], "centre": [r3(xt[t] + HGW / 2), cen_y]} for t in range(4)]
far = max(abs(r["centre"][0] - regions[0]["centre"][0]) for r in regions[1:])
print(f"attw_lp outline {W} x {H} (aspect {W / H:.2f}); c column x {xc}..{xc + CW}; tiles x {xt}; "
      f"farthest landed crossing {far:.0f} um; macros {len(ms)}", file=sys.stderr)

# ------------------------------------------------------------------ lp.py spec
lp = {
    "top": "dsdv_svc_attw_f",
    "why": "SVC4 (LEAD2-S81 10-19): attw (dsdv_svc_rs_attw at the PRODUCTION engine, 16 hard s81svc_attn_hgrp) is a "
           f"~{W / 1000:.1f} x {H / 1000:.1f} mm parent -> landed parent: region c = the attention share (u_c, centre "
           "column with every SRAM), regions t0..t3 = one per engine tile (u_t<k>, 4 hard head groups). The c<->tile loop "
           "(issue -> tile -> lane trees) is re-scheduled: schedule 'reference', ref TLX = TXD = 6 (+3 edges per landed "
           "crossing, both ways), landed TLX 6 / TXD 0.",
    "sources": [f"{D}/attw/dsdv_svc_attw_f.sv"],
    "child_sources": SRC,
    "include_dirs": [D],
    "defines": DEFS,
    "params": dict(PAR, TLX=6, TXD=0),
    "ref_params": dict(PAR, TLX=6, TXD=6),
    "schedule": "reference",
    "out_dir": f"{D}/attw/lp",
    "record_dir": "results/arch/landed_parent_1018/dsdv_svc_attw_f",
    "clock_ports": ["ck"],
    "clock_pins": ["ck", "clk"],
    "reset_port": "rst",
    "reset_pins": ["rst", "rst_n"],
    "static": ["sid"],
    "tb_static": {"sid": "4'd3"},
    "regions": regions,
    "bench": {"cycles": 6000, "reset_cycles": 24, "sim": "verilator"},
    "mut_child": "u_c",
}
(ROOT / "tools/landed_parent/specs/dsdv_svc_attw_f.json").write_text(json.dumps(lp, indent=1) + "\n")

# ------------------------------------------------------------------ ref_tile kit spec (landed top)
ports_n = ["cs", "qrk", "qwd", "qrv", "qr_data", "qr_tag", "qr_beat", "qrq"]
ports_s = ["l_v", "l_d", "pv_ov", "pv_od", "sm_st", "sm_kind", "sm_jid", "sm_rv", "sm_rp", "sm_rj", "sm_rd",
           "go_o", "tjob_o", "done", "tagj", "hcr", "hack", "fault", "sid", "rst"]
kit = {
    "name": "dsdv_svc_attw_f_lp",
    "top": "dsdv_svc_attw_f_lp",
    "kind": "cluster",
    "sources": [f"{D}/attw/lp/dsdv_svc_attw_f_lp.sv", f"{D}/attw/dsdv_svc_attw_f.sv"] + SRC +
               ["rtl/common/landed_parent/ot_pl_land.sv"],
    "params": dict(PAR, TLX=6, TXD=0, MUT=0),
    "defines": DEFS,
    "orfs_vars": {"VERILOG_INCLUDE_DIRS": f"/src/{D}", "SYNTH_ARGS": "-noshare", "SYNTH_MEMORY_MAX_BITS": "163840"},
    "clock": "cts",
    "clock_port": "ck_c",
    "clock_ports": ["ck_c", "ck_t0", "ck_t1", "ck_t2", "ck_t3"],
    "reset_ports": ["rst"],
    "sdc_extra": [f"{D}/attw/lp/dsdv_svc_attw_f_lp.sdc"],
    "outline": {"w": W, "h": H},
    "cluster_level": 2,
    "children": ch,
    "macros": ms,
    "pins": {"N": ports_n, "S": ["ck_t0", "ck_t1"] + ports_s[:len(ports_s) // 2] + ["ck_c"] + ports_s[len(ports_s) // 2:] +
             ["ck_t2", "ck_t3"]},
    "recipe": 4,
    "hold_budget": "die",
    "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 256, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
              "macro_halo_um": 5.4},
    "reset_landing": {"enable": True, "stages": 2},
    "pin_regs": {"enable": False, "reason": "source-registered: -DOT_SVC_ATT_PINREG registers every attw input pin "
                 "(q/hw/qr_*) and the fault OR; every other output is a dsdv_svc_att_core flop (SVC2 809c78aa5)"},
    "structural_change": "SVC4: attw at the production engine as a LANDED PARENT (5 regions: c + 4 engine tiles, 16 hard "
                         "head groups, every tile bundle landed both ways, TLX 6 engine re-schedule); centre SRAM column "
                         "so region c stays compact",
}
(ROOT / "tools/ref_tile/specs_s81dv_svc_lp/dsdv_svc_attw_f_lp.json").write_text(json.dumps(kit, indent=1) + "\n")
