#!/usr/bin/env python3
"""STW-S81c-TOK4-BAND 10-22: kit spec of the banded idx rg3 MAIN landed parent dsdv_idx_rg3_bf_lp (4 hard band children
R / X / S01 / S23 on their CLOSED views, one clock root per band region, every crossing landed D2/E1 by lp.py).  Run after
the band views exist:  python3 results/arch/s81_band_1022/mk_rg3_lp_kit.py [--commit C]"""
import json, subprocess, sys, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
base = json.loads((ROOT / "physical/ref_tile/s81dv_idxrg3p/spec.json").read_text())
LP = "rtl/dsrom_sys/s81_dv/idx/lp/dsdv_idx_rg3_bf_lp.sv"
name = "s81dv_rg3b_lp"
kids = [("u_r", "s81dv_rg3b_r", "dsdv_idx_rg3_br", [0.0, 1209.6]), ("u_x", "s81dv_rg3b_x", "dsdv_idx_rg3_bx", [518.4, 1123.2]),
        ("u_s01", "s81dv_rg3b_s01", "dsdv_idx_rg3_bs01", [0.0, 0.0]), ("u_s23", "s81dv_rg3b_s23", "dsdv_idx_rg3_bs23", [518.4, 0.0])]
s = {k: copy.deepcopy(base[k]) for k in ("recipe", "io_flop_at_pins", "keep_pin_regs", "inter")}
s.update(
    name=name, top="dsdv_idx_rg3_bf_lp", kind="cluster",
    sources=["rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_n32.sv",
             "rtl/common/landed_parent/ot_pl_land_rst_copy.sv", LP],
    params={"MUTR": 0, "SRAM_MACRO": 1, "RH": 1, "KR": 1, "LX": 8, "PD": 2},
    clock_port="ck_r", reset_ports=["rst"], outline={"w": 993.6, "h": 1555.2, "exact": True},
    children=[dict(view=f"physical/ref_tile/{k}/views/{t}", count=1, inst=i, at=a, orient="R0") for i, k, t, a in kids],
    macros=[], defines=[],
    pins={"W": ["qi", "si", "sid", "rst", "ck_r", "ck_s01"], "N": ["rqo", "rri", "ck_x"], "E": ["qo", "so", "st", "ck_s23"]},
    pin_ranges={"qi": [1252.8, 1512.0], "si": [1252.8, 1512.0], "sid": [1252.8, 1512.0], "rst": [1252.8, 1512.0],
                "ck_r": [1360.8, 1367.28], "ck_s01": [540.0, 546.48], "rqo": [21.6, 453.6], "rri": [540.0, 972.0],
                "ck_x": [745.2, 751.68], "qo": [43.2, 1036.8], "so": [43.2, 1036.8], "st": [43.2, 1036.8], "ck_s23": [540.0, 546.48]},
    layer_cap="M6", layer_cap_grant="STW-S81c-TOK4 (steward-delegated): landed band parent over M5-capped hard bands; parent "
                                    "landing halves / crossings on M6 as every landed parent (seq b1m, qwen clusters)",
    route={"pd": 0.5, "threads": 16, "peak_ram_gb": 64, "hold_margin_ns": 0.03,
           "pin_balance": {"group_max": 1, "h": "M4 M6", "v": "M5"}, "macro_halo_um": 5.4},
    pin_regs={"enable": False, "reason": "landed wires-only parent: every parent port lands in a hard band's pin flop or "
                                          "a parent landing half (lp.py); a recipe pin stage would add an unbooked edge"},
    inhold=True, outhold=True, hold_pad={"cell": "HB2xp67_ASAP7_75t_R"},
    reset_landing={"enable": False, "reason": "lp.py regional reset runs (depth 5) + each band's own 2-stage forest"},
    child_clock_ref="boundary", clock="multiple_cts_roots", clock_ports=["ck_r", "ck_x", "ck_s01", "ck_s23"],
    clock_data_paths="related_same_frequency", clock_relationship={"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
    landed_record="results/arch/s81_band_1022/landed/dsdv_idx_rg3_bf_lp_record.json",
    clock_entry_domains={"r": {"ratio": [1, 1], "ports": ["ck_r"], "inputs": ["rst", "sid", "qi", "si"], "outputs": ["rqo"]},
                         "x": {"ratio": [1, 1], "ports": ["ck_x"], "inputs": ["rri"], "outputs": []},
                         "s01": {"ratio": [1, 1], "ports": ["ck_s01"], "inputs": [], "outputs": []},
                         "s23": {"ratio": [1, 1], "ports": ["ck_s23"], "inputs": [], "outputs": ["qo", "so", "st"]}},
    child_centre_tap={"children": [k[0] for k in kids], "why": "one root per band region; per-root clock buffer chains "
                      "matched to each CLOSED band's TT/FF/SS boundary insertion (80 ps gate unchanged)"},
    structural_change="STW-S81c-TOK4-BAND 10-22 (MU.BAL.SX.3): idx rg3 clock-rule successor parent: 4 CLOSED hard bands "
                      "R / X / S01 / S23 (each its own small tree) under an lp.py landed parent (D2/E1, 12 landings, +2 edges a "
                      "crossing, booked with STW-S81c-DIE3 16:36); frozen dsdv_idx_rg3 ports via dsdv_idx_rg3_lpw (one die ck "
                      "feeds ck_r / ck_x / ck_s01 / ck_s23).",
    why_floorplan="R NW (0, 1209.6) / X NE (518.4, 1123.2) / S01 SW (0, 0) / S23 SE (518.4, 0); channels x 475-518 (R <-> X "
                  "and S01 <-> S23 landings), y 1080-1123 / 1080-1210 (R -> S, X -> S landings) hold the soft landing halves.",
    job={"owner": "Claude:STW-S81c-TOK4-BAND", "branch": "claude/s81-band-1022", "tag": name,
         "purpose": "banded idx rg3 MAIN landed parent on the closed band views", "views_to": f"physical/ref_tile/{name}/views",
         "record_to": f"results/rtl/ref_tile/{name}",
         "extra_paths": ["rtl/common/landed_parent", "rtl/dsrom_sys/s81_dv/idx", "results/arch/s81_band_1022"]
                        + [f"physical/ref_tile/{k[1]}" for k in kids]})
d = ROOT / "physical/ref_tile" / name; d.mkdir(parents=True, exist_ok=True)
(d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
r = subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(d / "spec.json")] + sys.argv[1:],
                   cwd=ROOT, capture_output=True, text=True)
print(name, "rc", r.returncode, (r.stdout + r.stderr).strip().splitlines()[-4:])
