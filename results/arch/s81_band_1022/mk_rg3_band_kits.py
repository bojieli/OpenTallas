#!/usr/bin/env python3
"""STW-S81c-TOK4-BAND 10-22: write the band kit specs of the banded idx rg3 (MAIN: R / X / S01 / S23) from the rg3p kit
spec, then `ref_tile.py gen` each.  Parent outline 993.6 x 1555.2 (aspect 1.57), every band origin on the 43.2 lattice:
  R   (0, 1209.6)    475.2 x 345.6   NW: W pins qi/si/sid/rst/ck, N rqo, S face down to S01 / S23 inputs; 5 SRAM (2 x 3)
  X   (518.4, 1123.2) 475.2 x 432   NE: N rri (2.5 pins/um), W to R, S kq to S01 / S23; 8 landing SRAM (2 cols x 4)
  S01 (0, 0)         475.2 x 1080   16 hslice (2 columns x 8, slice 0 on top); layer cap M5 (R -> S23 crosses on M6)
  S23 (518.4, 0)     475.2 x 1080   16 hslice; E pins qo / so / st = the parent's
  channels: x 475.2-518.4 between R and X (R <-> X landings), y 1080-1209.6 under R (R -> S landings), seam x 475-518
  python3 results/arch/s81_band_1022/mk_rg3_band_kits.py [--commit C]"""
import json, subprocess, sys, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
base = json.loads((ROOT / "physical/ref_tile/s81dv_idxrg3p/spec.json").read_text())
SRAM = "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2"
HS = "physical/ref_tile/ot_hdc_v41x_idx_hslice_m5/views/ot_hdc_v41x_idx_hslice"
SRC = [s for s in base["sources"] if not s.endswith("dsdv_idx_rg3.sv")]
BR, BAND = "rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3_br.sv", "rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3_band.sv"
BENCH_LP = ("bash rtl/dsrom_sys/s81_dv/idx/test/run_rg3_band_lp.sh {RUN} lpc0 '-GMUT=0 -GSRAM_MACRO=1 -GIH=0 -GOH=3 -GKR=1 -GRH=1' 8 "
            "'pass_small|+N=4096 +B=13 +T0=400 +P=3' 'pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4' "
            "'pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6' 'pass_l20|+N=87382 +B=13 +T0=400 +P=3' "
            "'closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3' 'closed_late|+N=4096 +B=13 +T0=60 +P=3' "
            "'fail_slothit|+N=4096 +B=13 +T0=400 +P=3 +SLOTHIT=1'")
BENCH_LPM = ("bash rtl/dsrom_sys/s81_dv/idx/test/run_rg3_band_lp.sh {RUN} lpm1k '-GMUT=0 -GSRAM_MACRO=1 -GIH=0 -GOH=3 -GKR=1 -GRH=1 "
             "-DOT_LPW_LPMUT=1' 8 'pass_small|+N=4096 +B=13 +T0=400 +P=3' 'pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4'")
WHY = ("STW-S81c-TOK4-BAND 10-22 (STEWARD-S81c item, MU.BAL.SX.3): idx rg3 clock-rule successor. rg3p / rg3nqq2 hung 27-32k "
       "sinks on ONE ck over 1.04 x 1.21 mm (TT spread 223-233 ps; k-means under one port cannot fix it). The reader is cut at "
       "existing registers into 4 hard bands (R control / X response + landing + key mux / S01 / S23 engine halves), each "
       "its own small tree with registered faces, under an lp.py landed parent (D2/E1, +2 edges a crossing; cut analysis "
       "results/arch/s81_band_1022/cut_analysis.json: every seam <= 0.16 of its tracks). Flat band composition = dsdv_idx_rg3 "
       "#(IH 0, OH 1, KR 1) cycle-exact (tb lockstep); landed = flat + 2-edge landings (lp.py lockstep) with LX 8 / PD 2.")

def job(name, purpose):
    return dict(owner="Claude:STW-S81c-TOK4-BAND", branch="claude/s81-band-1022", tag=name, purpose=purpose,
                views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
                extra_paths=["rtl/dsrom_sys/s81_dv/idx", "rtl/dsrom_sys/s81_ph", "rtl/dsrom_sys/s81_glue",
                             "rtl/dsrom_sys/s81_dv/unit/bk", "rtl/hdc", "rtl/lib", "rtl/common/landed_parent", "tools/landed_parent",
                             SRAM, "physical/ref_tile/ot_hdc_v41x_idx_hslice_m5"],
                benches=[dict(name="rg3b_lpc0", cmd=BENCH_LP, expect="pass", pass_regex="^IDXRD_CAMPAIGN PASS",
                              threads=16, peak_ram_gb=64, needs=["verilator"]),
                         # expect=fail mutant: the landed parent's MUT 1 (xr landing bypass) under the PASS cases
                         dict(name="rg3b_lpm1", cmd=BENCH_LPM, expect="fail", fail_regex="^IDXRD_CASE BAD lpm1k/pass_[a-z0-9]+: TB_IDXRD FAIL . TB_IDXRD_STATS",
                              threads=16, peak_ram_gb=64, needs=["verilator"])])

def common(name, top, purpose):
    s = {k: copy.deepcopy(base[k]) for k in ("route", "keep_pin_regs", "io_flop_at_pins", "reset_landing", "recipe",
                                             "inhold", "outhold", "inter", "orfs_vars")}
    s.update(name=name, top=top, clock_port="ck", reset_ports=["rst"], structural_change=WHY, job=job(name, purpose),
             pin_regs={"enable": False, "reason": "band of the banded idx rg3: source-registered faces (every band input lands "
                       "in a flop, every output leaves one: the landed parent's ring / read halves sit outside); a recipe "
                       "pin stage would add an unpriced edge on the landed schedule (lp record)."})
    s["route"]["peak_ram_gb"] = 48
    return s

def hs_children(prefix):
    return [dict(view=HS, inst=f"u_cols.g_ch[{c}].u_c.g_s[{k}].u_s", at=[86.4 + 172.8 * c, round(43.2 + (7 - k) * 129.6, 2)])
            for c in range(2) for k in range(8)]

specs = {}
r = common("s81dv_rg3b_r", "dsdv_idx_rg3_br", "banded idx rg3 MAIN: R band (reader control, chain front, rqo), 5 SRAM")
r.update(kind="tile", sources=SRC + [BR], params={"SRAM_MACRO": 1, "KR": 1, "IH": 0, "LX": 8},
         outline={"w": 475.2, "h": 345.6, "exact": True},
         macros=[dict(view=SRAM, inst=i, at=[43.2 + 216.0 * (n % 2), round(43.2 + 90.72 * (n // 2), 2)]) for n, i in
                 enumerate(["u_sq.g_m.u_mem", "u_mq.g_m.u_mem", "u_iq.g_m.u_mem", "g_lm[0].u_mem.g_m.u_mem", "g_lm[1].u_mem.g_m.u_mem"])],
         children=[], pins={"W": ["qi", "si", "sid", "rst"], "N": ["rqo"],
                            "S": ["qoi_o", "soi_o", "st_o", "ql_o", "sc_i", "ck"], "E": ["sx_o", "xr_i"]},
         pin_ranges={"qi": [43.2, 302.4], "si": [43.2, 302.4], "sid": [43.2, 302.4], "rst": [43.2, 302.4], "ck": [229.68, 236.16],
                     "rqo": [21.6, 453.6], "qoi_o": [21.6, 410.4], "soi_o": [21.6, 410.4], "st_o": [21.6, 410.4],
                     "ql_o": [21.6, 410.4], "sc_i": [410.4, 453.6], "sx_o": [43.2, 302.4], "xr_i": [43.2, 302.4]},
         layer_cap="M5", defines=[], std_area_um2=4000,
         why_floorplan="NW tile (475.2 x 345.6, parent (0, 1209.6)) of the banded rg3 parent, sized to its content (5 SRAM "
                       "+ ~7k flops, fill ~42 %): 5 SRAM in 2 columns x 3 rows (x 43.2 / 259.2, 41-um gap and edge channels; y 43.2 up so the "
                       "S pin face keeps a 43-um halo), W pins qi/si/sid/rst/ck, N rqo (parent N face, as rg3p), S face = "
                       "the q / s chain, query load and status out down to the S bands' top input stages (2.2 pins/um) + sc "
                       "in at the SE corner, E face to X across the 43-um landing channel (S stage out, response control in).")
r["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
r["route"]["cts_sink"] = {"sink_clustering": False, "extra": "-no_obstruction_aware"}   # sparse SRAM tile, pin-band sinks (qkd_d2d_static recipe); R gate 10-22: clustered tree 462..725 ps
specs[r["name"]] = r
# R fallback (parallel): same tile, H-tree buffers every 40 um (qkd_astk_ep: long leaf strings left far leaves late)
rb = copy.deepcopy(r); rb["name"] = "s81dv_rg3b_rb"; rb["job"] = job("s81dv_rg3b_rb", r["job"]["purpose"] + " (FB: CTS buffer pitch 40 um)")
# gate 3 (10-22 17:4x): S-centre entry 109 / +40-um pitch 113 ps: the ~130 pin flops sit at the pins of all FOUR faces of a
# sparse SRAM tile (754 um2 std) -> MAIN: pin flops placed with their logic (io_flop_at_pins off; the parent landing
# halves are the timed boundary anyway); FB: pins on two faces only (W + S, clock at the SW corner)
r["io_flop_at_pins"] = False
rb["route"]["cts_sink"] = {"sink_clustering": False, "extra": "-no_obstruction_aware"}
rb["pins"] = {"W": ["rqo", "qi", "si", "sid", "rst"], "S": ["ck", "sc_i", "qoi_o", "soi_o", "st_o", "ql_o", "sx_o", "xr_i"]}
rb["pin_ranges"] = {"rqo": [237.6, 324.0], "qi": [21.6, 237.6], "si": [21.6, 237.6], "sid": [21.6, 237.6], "rst": [21.6, 237.6],
                    "ck": [10.8, 17.28], "sc_i": [21.6, 43.2], "qoi_o": [43.2, 345.6], "soi_o": [43.2, 345.6], "st_o": [43.2, 345.6],
                    "ql_o": [43.2, 345.6], "sx_o": [367.2, 453.6], "xr_i": [367.2, 453.6]}
specs[rb["name"]] = rb
# gate 4: io_flop_at_pins off 89 / 84 ps -> rc = both (two pin faces + pin flops with their logic)
rc = copy.deepcopy(rb); rc["name"] = "s81dv_rg3b_rc"; rc["io_flop_at_pins"] = False
rc["job"] = job("s81dv_rg3b_rc", r["job"]["purpose"] + " (FB2: W+S pins, SW clock, pin flops with logic)")
specs[rc["name"]] = rc
x = common("s81dv_rg3b_x", "dsdv_idx_rg3_bx", "banded idx rg3 MAIN: X band (response lanes, landing SRAMs, key mux)")
x.update(kind="tile", sources=SRC + [BAND], params={"SRAM_MACRO": 1, "RH": 1},
         outline={"w": 475.2, "h": 432.0, "exact": True},
         macros=[dict(view=SRAM, inst=f"g_land[{u}].u_h{h}.g_m.u_mem", at=[43.2 + 216.0 * h, round(43.2 + 90.72 * u, 2)])
                 for u in range(4) for h in range(2)],
         children=[], pins={"N": ["rri"], "W": ["sx_i", "xr_o", "rst", "ck"], "S": ["kq_o"]},
         pin_ranges={"rri": [21.6, 453.6], "kq_o": [21.6, 453.6], "sx_i": [86.4, 345.6], "xr_o": [86.4, 345.6],
                     "rst": [86.4, 345.6], "ck": [86.4, 345.6]},
         layer_cap="M5", defines=[], std_area_um2=3000,
         why_floorplan="NE tile (475.2 x 432, parent (518.4, 1123.2)) over S23: rri N pins over the face (1,088 / 432 um = "
                       "2.5/um), lane relays + landing writes in the 46-um top band, 8 landing SRAM in 2 columns (h0 / h1) "
                       "x 4 rows (unit u), so the 4-way key mux (SRAM read -> kq) spans <= ~400 um (a 4 x 2 row of SRAM "
                       "over 994 um put 800-um wires in that one cycle); kq on the S face toward both S bands, W face to R.")
x["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
x["route"]["cts_sink"] = {"sink_clustering": False, "extra": "-no_obstruction_aware"}   # sparse SRAM tile, pin-band sinks (qkd_d2d_static recipe); R gate 10-22: clustered tree 462..725 ps
specs[x["name"]] = x
for nm, top, extra_pins, cap in (("s81dv_rg3b_s01", "dsdv_idx_rg3_bs01", {"N": ["kq_i", "qoi_i", "ql_i"], "W": ["rst", "ck"],
                                                                         "E": ["a0_o"]}, "M5"),
                                 ("s81dv_rg3b_s23", "dsdv_idx_rg3_bs23",
                                  {"N": ["kq_i", "qoi_i", "soi_i", "st_i", "ql_i"], "W": ["a0_i", "sc_o", "rst", "ck"],
                                   "E": ["qo", "so", "st"]}, "M6")):
    s = common(nm, top, f"banded idx rg3 MAIN: {nm[-3:].upper()} band (2 chunk columns, 16 hslice children, tail part)")
    pins = dict(extra_pins)
    pr = {"kq_i": [21.6, 453.6], "qoi_i": [21.6, 453.6], "ql_i": [21.6, 453.6], "soi_i": [21.6, 453.6],
          "st_i": [21.6, 453.6], "a0_i": [0.0, 216.0], "a0_o": [0.0, 216.0], "sc_o": [0.0, 216.0],
          "rst": [432.0, 604.8], "ck": [432.0, 604.8], "qo": [43.2, 1036.8], "so": [43.2, 1036.8], "st": [43.2, 1036.8]}
    s.update(kind="cluster", sources=SRC + [BAND], params={"KR": 1} | ({"PD": 2} if nm.endswith("s23") else {}),
             outline={"w": 475.2, "h": 1080.0, "exact": True}, macros=[], children=hs_children(nm), pins=pins,
             pin_ranges={k: v for k, v in pr.items() if any(k in p for p in pins.values())},
             layer_cap=cap, defines=["OT_IDX_HSLICE_HARD"], hard_define="OT_IDX_HSLICE_HARD", std_area_um2=3000,
             why_floorplan=("2 abutted hslice chunk columns x 86.4 / 259.2 (the rg3p column pitch; 86.4 W margin for the R inputs), slices 0..7 top -> bottom on "
                            "the 129.6 pitch (25.9-um seams, chain N -> S); top band = shared code / head / valid input stages under "
                            "the N face (key from X, q / s / query load from R, <= 2.9 pins/um); bottom band = chunk sums -> "
                            "tail half; tail link a0 / sc on the W / E foot"
                            + ("; layer cap M5 so the R -> S23 landings cross this band on M6." if cap == "M5" else
                               "; q / s / st output stage spans the band W -> E above the columns (E pins = the reader's qo / so / st).")))
    specs[nm] = s
# ---- X successor (gate 10-22 18:2x: flat X FAIL TT / FF pin-flop spread 230.6 / 201.2 ps, 4,021 sinks: the N rri pin flops
# and the S kq pin flops sat 432 um apart around 8 SRAM covering ~60 % of the tile, one root).  STRUCTURAL: X is cut at its
# existing registers into two hard tiles under a wires-only X cluster (475.2 x 518.4, parent grows 86.4 at the top):
#   xn  dsdv_idx_rg3_bxn  475.2 x 86.4 landing strip, NO macros: rri pin flops N, registered landing writes lw_* S, xr_o W
#   xm  dsdv_idx_rg3_bxm  475.2 x 432: the 8 SRAM + read / key, ONE pin-flop band (kq, S face) on the clock-entry side;
#       h0 column R0 (read pins on the W channel), h1 column MY (read pins on the E channel): each key half is column-local,
#       write pins of both columns face the 39-um centre gap under the lw_* N face (macro inputs, no flops)
#   xmb FB of xm: same tile, clock at the SW corner of the kq face (rb's geometry) instead of the S-face centre
# Cycle-exact to the flat X (tb_dsdv_idx_rg3_bx_lsw: 2 seeds x 20k edges 0 mismatches; MUT 5 caught).
LSWX = dict(name="rg3b_bx_lsw", cmd="bash rtl/dsrom_sys/s81_dv/idx/test/run_rg3_bx_lsw.sh {RUN} 20000 0", expect="pass",
            pass_regex="^BX_LSW PASS$", threads=4, peak_ram_gb=8, needs=["verilator"])
LSWX_M = dict(name="rg3b_bx_lsw_mut5", cmd="bash rtl/dsrom_sys/s81_dv/idx/test/run_rg3_bx_lsw.sh {RUN} 20000 5", expect="fail",
              fail_regex="^BX_LSW MUTANT_CAUGHT$", threads=4, peak_ram_gb=8, needs=["verilator"])
xn = common("s81dv_rg3b_xn", "dsdv_idx_rg3_bxn", "banded idx rg3 X successor: landing strip (rri pin flops, lane register, landing writes)")
xn.update(kind="tile", sources=SRC + [BAND], params={"RH": 1}, outline={"w": 475.2, "h": 86.4, "exact": True}, macros=[],
          children=[], pins={"N": ["rri"], "S": ["lw_v", "lw_h1", "lw_a", "lw_d"], "W": ["xr_o", "rst", "ck"]},
          pin_ranges={"rri": [21.6, 453.6], "lw_v": [21.6, 453.6], "lw_h1": [21.6, 453.6], "lw_a": [21.6, 453.6],
                      "lw_d": [21.6, 453.6], "xr_o": [10.8, 75.6], "rst": [10.8, 75.6], "ck": [40.0, 46.4]},
          layer_cap="M5", defines=[], std_area_um2=2500,
          why_floorplan="top strip of the X cluster (475.2 x 86.4): ~3.3k flops in two pin bands 86 um apart (rri N 2.5 pins/um "
                        "from the die response lanes, lw_* S 2.5 pins/um straight down onto the SRAM write pins of xm), "
                        "xr_o W toward R, clock at the W-face middle; no macros, so the tree spans 86 um.")
xn["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
xn["job"]["benches"] = [LSWX, LSWX_M]
specs[xn["name"]] = xn
def xm_spec(name, ck_range, purpose, note):
    m = common(name, "dsdv_idx_rg3_bxm", purpose)
    m.update(kind="tile", sources=SRC + [BAND], params={"SRAM_MACRO": 1}, outline={"w": 475.2, "h": 432.0, "exact": True},
             macros=[dict(view=SRAM, inst=f"u_c{h}.g_land[{u}].u_h.g_m.u_mem", at=[[43.2, 257.04][h], round(43.2 + 90.72 * u, 2)],
                          orient=["R0", "MY"][h]) for h in range(2) for u in range(4)],
             children=[], pins={"N": ["lw_v", "lw_h1", "lw_a", "lw_d"], "W": ["sx_i", "rst"], "S": ["kq_o", "ck"]},
             pin_ranges={"lw_v": [21.6, 453.6], "lw_h1": [21.6, 453.6], "lw_a": [21.6, 453.6], "lw_d": [21.6, 453.6],
                         "sx_i": [86.4, 172.8], "rst": [86.4, 172.8], "kq_o": [21.6, 453.6], "ck": ck_range},
             layer_cap="M5", defines=[], std_area_um2=2000,
             why_floorplan="SRAM tile of the X cluster (475.2 x 432 under xn): 8 SRAM in 2 columns x 4 rows (90.72 pitch: 20-um "
                           "channels, the v1 SRAM LEF only sits on the snapped macro lattice so it cannot abut; y 43.2 .. 385.8: "
                           "43-um S halo over the kq pin band, 46-um N halo under the lw_* face); h0 column R0 "
                           "at x 43.2 (read pins on the 43-um W channel), h1 column MY at x 257.04 (read pins on the E channel): "
                           "each key half reads only its own column, so its mux runs down its own channel to the kq pin flops; "
                           "write pins of both columns face the 39-um centre gap.  The ONLY pin-flop band is kq on the S face, "
                           + note)
    m["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
    m["route"]["cts_sink"] = {"sink_clustering": False, "extra": "-no_obstruction_aware"}
    m["job"]["benches"] = [LSWX, LSWX_M]
    specs[name] = m
xm_spec("s81dv_rg3b_xm", [234.36, 240.84], "banded idx rg3 X successor MAIN: SRAM / key tile, clock at the kq face centre",
        "clock entry at its centre.")
xm_spec("s81dv_rg3b_xmb", [10.8, 17.28], "banded idx rg3 X successor FB: SRAM / key tile, clock at the SW corner of the kq face",
        "clock entry at its SW corner (the rb geometry that passed R at 52 / 79 ps).")
ONLY = None
if "--only" in sys.argv:
    i = sys.argv.index("--only"); ONLY = set(sys.argv[i + 1].split(",")); del sys.argv[i:i + 2]
for nm, s in specs.items():
    if ONLY is not None and nm not in ONLY:
        continue
    d = ROOT / "physical/ref_tile" / nm
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    cmd = [sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(d / "spec.json")] + sys.argv[1:]
    r_ = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(nm, "rc", r_.returncode, (r_.stdout + r_.stderr).strip().splitlines()[-3:])
