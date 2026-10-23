#!/usr/bin/env python3
"""STW-S81c-TOK4-BAND 10-22: band kit specs of the banded gunit l1f (MAIN: 3 row bands A_lo / F / A_hi) from the
dsdv_gunit_l1f_m kit spec, then `ref_tile.py gen` each.  Parent outline 432 x 518.4, 21.6-um seams:
  A_lo (0, 0)      432 x 151.2   bias macro 0, 8 adders, keys, sort8 #0; W bias pins; N face = F seam (2.2 pins/um)
  F    (0, 172.8)  432 x 172.8   W stack inputs (2.8/um), SC store, select control, gather, merge, E outputs (1.7/um)
  A_hi (0, 367.2)  432 x 151.2   bias macro 1, lanes 8..15; S face = F seam
  python3 results/arch/s81_band_1022/mk_l1f_band_kits.py [--commit C]"""
import json, subprocess, sys, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
base = json.loads((ROOT / "physical/ref_tile/dsdv_gunit_l1f_m/spec.json").read_text())
BIAS = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"
SRC = base["sources"] + ["rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f_band.sv"]
WHY = ("STW-S81c-TOK4-BAND 10-22 (STEWARD-S81c item, S81.STA.PAR.3): gunit l1f clock-rule successor. l1f_m hung 25,954 "
       "sinks on ONE clk (TT spread 162 / FF 139 ps, trial GRT overflow 595): the front is cut at existing registers into 3 "
       "hard row bands (A_lo / F / A_hi, ~7.5k / ~10k / ~7.5k flops), each its own small tree, under a single-root wires-only "
       "parent (dsdv_gunit_l1f_bp, < 0.6 mm: plain flop-to-flop hops, ZERO latency change; lockstep vs dsdv_gunit_l1f in "
       "the dsdv_gunit golden bench, run_l1f_band_lsw.sh).")
BENCH = dict(name="l1f_band_lsw", cmd="bash rtl/dsrom_sys/s81_dv/unit/test/run_l1f_band_lsw.sh {RUN} 8 '0 1'", expect="pass",
             pass_regex="^L1F_LSW PASS", threads=12, peak_ram_gb=48, needs=["verilator"])
# expect=fail mutant (submit_exact BENCH-EVIDENCE): the banded copy alone runs MUT 1 (bias forced 0) -> lockstep mismatches
BENCH_MUT = dict(name="l1f_band_lsw_bandmut", cmd="BANDMUT=1 bash rtl/dsrom_sys/s81_dv/unit/test/run_l1f_band_lsw.sh {RUN} 8 '0'",
                 expect="fail", fail_regex="^L1F_LSW FAIL band mutant caught", threads=12, peak_ram_gb=48, needs=["verilator"])

def kit(name, top, purpose, outline, macros, pins, pin_ranges, why):
    s = {k: copy.deepcopy(base[k]) for k in ("recipe", "clock", "hold_budget", "inter", "inhold", "outhold", "io_flop_at_pins",
                                             "keep_pin_regs", "reset_landing", "defines")}
    s["route"] = copy.deepcopy(base["route"]); s["route"]["peak_ram_gb"] = 48
    if top != "dsdv_gunit_l1f_bf":   # the A bands hold no store / decode: only the select-network keeps apply
        s["route"]["synth_keep_modules"] = [m for m in s["route"]["synth_keep_modules"] if m.startswith("dsdv_seln")]
    j = copy.deepcopy(base["job"])
    j.update(owner="Claude:STW-S81c-TOK4-BAND", branch="claude/s81-band-1022", tag=name, purpose=purpose, benches=[BENCH, BENCH_MUT],
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    j.pop("pass_witness", None)
    s.update(name=name, top=top, kind="tile", sources=SRC, params={}, clock_port="clk", reset_ports=["rst_n"],
             macros=macros, children=[], pins=pins, pin_ranges=pin_ranges, outline={"w": outline[0], "h": outline[1], "exact": True},
             layer_cap="M5", structural_change=WHY, why_floorplan=why, job=j,
             pin_regs={"enable": False, "reason": "band of the banded gunit l1f: source-registered faces (every band input "
                       "lands in a flop or a macro pin flop, every output leaves a flop; the merge fold / fault AND sit after "
                       "the A bands' sort / adder flops exactly as in dsdv_gunit_l1f); a recipe pin stage adds an unpriced edge."})
    return s

A_IN = ["re", "ra", "bw_e", "bw_a", "bw_d", "rst_n", "clk"]
specs = []
for lh, top in ((0, "dsdv_gunit_l1f_ba0"), (1, "dsdv_gunit_l1f_ba1")):
    seam = "N" if lh == 0 else "S"
    outs = ["sv", "ctl", "qa", "qb", "vf"] + (["fo"] if lh == 0 else [])
    specs.append(kit(f"s81dv_l1fb_a{lh}", top, f"banded gunit l1f MAIN: A_{'lo' if lh == 0 else 'hi'} band (bias macro {lh}, lanes {8*lh}..{8*lh+7})",
                     (432.0, 151.2), [dict(view=BIAS, count=1, at=[172.8, 21.6 if lh == 0 else 88.56])],
                     {"W": A_IN, seam: outs}, {p: [21.6, 410.4] for p in outs} | {p: [21.6, 129.6] for p in A_IN},
                     f"row band {'under' if lh == 0 else 'over'} F: bias macro {lh} centred on the {'S' if lh == 0 else 'N'} "
                     f"(pin-free) face, x 172.8, so its read word (-> s_bias -> the 8 adders' b operands) fans out <= 220 um; "
                     f"bias pins on the W face (as l1f_m); 8 adders + keys + sort8 between the macro and the {seam} seam face "
                     f"(s_val / control in, sort result / adder valid+error out, 953 pins over 389 um = 2.5/um)."))
f_w = ["sa_r", "sa_d", "sb_r", "sb_d", "we", "c_go", "c_fw", "c_l", "c_bn", "c_lvn", "rst_n", "clk"]
f_e = ["g_go", "g_hit", "g_a", "o_v", "o_f", "o_l", "o_g", "o_d", "o_flt"]
f_s = ["sv_lo", "ctl_lo", "s0a", "s0b", "sf0", "vf_lo"]; f_n = ["sv_hi", "ctl_hi", "s1a", "s1b", "vf_hi"]
specs.append(kit("s81dv_l1fb_f", "dsdv_gunit_l1f_bf", "banded gunit l1f MAIN: F band (inputs, SC store, select control, gather, merge, outputs)",
                 (432.0, 172.8), [], {"W": f_w, "E": f_e, "S": f_s, "N": f_n},
                 {p: [10.8, 162.0] for p in f_w + f_e} | {p: [21.6, 410.4] for p in f_s + f_n},
                 "middle row band: stack inputs on the W face (485 pins / 151 um = 3.2/um, as l1f_m's W face), the 3,584-b SC "
                 "store + write decode + beat read / forward in the W two thirds, merge (fold -> m1 -> cx8_2) + gather + the "
                 "246-b output stage on the E third under the E pins; S face = A_lo seam (sv_lo / control out, sort #0 in), "
                 "N face = A_hi seam."))
for s in specs:
    d = ROOT / "physical/ref_tile" / s["name"]; d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    r_ = subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(d / "spec.json")] + sys.argv[1:],
                        cwd=ROOT, capture_output=True, text=True)
    print(s["name"], "rc", r_.returncode, (r_.stdout + r_.stderr).strip().splitlines()[-3:])
