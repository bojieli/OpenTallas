#!/usr/bin/env python3
"""seq (B): spec.json of the hardened landing-band children (STW-S81c-COLLA2-VP 2026-10-22).
MAIN b1m: bands 388.8 wide x (lk 151.2 / vc 194.4), the gaps between the closed children.  FB b1f: same RTL, bands one
21.6-um row taller (lk 172.8 / vc 216.0: lower std/pin density, 10.8-um parent channels)."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
BANDS = ROOT / "rtl/dsrom_sys/s81_dv/unit/r3/dsdv_seq_host_c_r3_lb_bands.sv"
txt = BANDS.read_text()
SRC = ["rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_n32.sv",
       "rtl/common/landed_parent/ot_pl_land_rst_copy.sv", "rtl/dsrom_sys/s81_dv/unit/r3/dsdv_seq_host_c_r3_lb_bands.sv"]
def ports(mod):
    m = re.search(r"module " + mod + r" #\(.*?\) \((.*?)\);", txt, re.S)
    return [(d, n) for d, n in re.findall(r"(input|output) wire (?:\[[^\]]+\] )?(\w+)", m.group(1))]
# signal -> (face, domain): S = toward the child below, N = toward the child above
CFG = {
 "lk": {"clocks": ["ck_lk", "ck_sq"], "resets": ["rst_n_lk", "rst_n_sq"],
        "below": "u_l0", "above": "u_l1", "dom_below": "lk", "dom_above": "sq",
        "S_in": ["n01", "pw01", "pl01", "tw01", "cf01", "ks01", "jd01"], "N_in": ["s10", "kd10", "j10", "sq10", "vf10"],
        "extra": {"lpr_c_u_l0": ("S", "lk"), "lpr_c_u_l1": ("N", "sq"), "lpr_sq_p_o": ("N", "sq")},
        "h": {"m": 151.2, "f": 172.8}},
 "vc": {"clocks": ["ck_sq", "ck_vc"], "resets": ["rst_n_vc"],
        "below": "u_l1", "above": "u_l2", "dom_below": "sq", "dom_above": "vc",
        "S_in": ["n12", "tw12", "cn12", "cs12", "cf12", "cg12"], "N_in": ["s21", "dn21", "vf21"],
        "extra": {"lpr_c_u_l2": ("N", "vc"), "lpr_sq_p": ("S", "sq")},
        "h": {"m": 194.4, "f": 216.0}},
}
LINT = ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; MOD u_top (); endmodule' > {RUN}/ot_lint_top.sv && verilator --lint-only "
        "-Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv "
        + " ".join(SRC) + " && echo lint-ok")
W = "results/arch/seq_b1_bands_1022/witness"
BENCH = [
 {"name": "region_program_lb", "cmd": "J=4 bash tools/s81_dv/seq_three_roots_1021/run_program_lb.sh {RUN}/region_program 0", "expect": "pass",
  "pass_regex": "^SEQ_REGION_PROGRAM_PASS$", "pass_witness": f"{W}/prog0/run.log", "threads": 4, "peak_ram_gb": 16, "needs": ["verilator"]},
 {"name": "region_landing_lb", "cmd": "J=4 bash tools/s81_dv/seq_three_roots_1021/run_landing_lb.sh {RUN}/region_landing 0", "expect": "pass",
  "pass_regex": "^SEQ_REGION_LANDING_PASS$", "pass_witness": f"{W}/land0/run.log", "threads": 4, "peak_ram_gb": 16, "needs": ["verilator"]},
 {"name": "region_missing_landing_lb", "cmd": "J=4 bash tools/s81_dv/seq_three_roots_1021/run_landing_lb.sh {RUN}/region_missing_landing 1", "expect": "fail",
  "fail_regex": "^SEQ_REGION_MISSING_LANDING_CAUGHT$", "fail_witness": f"{W}/land1/run.log", "threads": 4, "peak_ram_gb": 16, "needs": ["verilator"]},
]
base = json.loads((ROOT / "physical/ref_tile/dsdv_seq_host_r3c/spec.json").read_text())
for b, c in CFG.items():
    mod = f"dsdv_sh_lb_{b}"
    ps = ports(mod)
    face, dom = {}, {}
    for d, n in ps:
        if n in c["clocks"]: face[n] = "E"; continue
        if n in c["resets"]: face[n] = "E"; dom[n] = {"rst_n_lk": "lk", "rst_n_sq": "sq", "rst_n_vc": "vc"}[n]; continue
        if n in c["extra"]: face[n], dom[n] = c["extra"][n]; continue
        base_n = n.split("__l_")[0]
        if base_n in c["S_in"]:   # written below (input on S), landed above (output on N)
            face[n] = "S" if d == "input" else "N"; dom[n] = c["dom_below"] if d == "input" else c["dom_above"]
        elif base_n in c["N_in"]:
            face[n] = "N" if d == "input" else "S"; dom[n] = c["dom_above"] if d == "input" else c["dom_below"]
        else:
            raise SystemExit(f"{mod}: unplaced port {n}")
    pins = {}
    for d, n in ps: pins.setdefault(face[n], []).append(n)
    doms = {}
    for ck in c["clocks"]:
        dn = ck[3:]
        doms["core" if ck == c["clocks"][0] else dn] = {"ratio": [1, 1], "ports": [ck],
                    "inputs": [n for d, n in ps if d == "input" and dom.get(n) == dn],
                    "outputs": [n for d, n in ps if d == "output" and dom.get(n) == dn]}
    for v in ("m", "f"):
        name = f"dsdv_sh_lb_{b}_b1{v}"
        s = {"name": name, "top": mod, "kind": "tile", "sources": SRC, "params": {"V": 276, "MUT": 0}, "defines": [],
             "clock": "multiple_cts_roots", "clock_port": c["clocks"][0], "clock_ports": c["clocks"],
             "clock_data_paths": "related_same_frequency", "clock_relationship": base["clock_relationship"],
             "clock_entry_domains": doms, "reset_ports": [n for n in c["resets"]],
             "outline": {"w": 388.8, "h": c["h"][v], "exact": True}, "pins": pins,
             "recipe": 4, "route": {"pd": 0.5, "threads": 8, "peak_ram_gb": 16, "hold_margin_ns": 0.03,
                                    "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}},
             "pin_regs": {"enable": False, "reason": "source-registered landing halves: every input lands in a write-half bank register at its pin, every output leaves the read-half output register (ot_pl_land_local_r.o)"},
             "io_flop_at_pins": {"cols": 4, "allow_none": True}, "keep_pin_regs": True, "pin_reg_split": True,
             "reset_landing": {"enable": False, "reason": "the band carries the landed parent's own regional reset runs (4-stage pads + kept copies), unchanged"},
             "inter": [], "macros": [], "children": [],
             "structural_change": (f"seq (B) hardened landing band {b} (STW-S81c-COLLA2-VP 10-22, steward-approved option B after r3c..r3f clock_child_pair "
                 "101-485 ps: the parent's soft landing halves sat under one root per region strung along 1,339-um faces). This child = the "
                 f"{'lk<->sq landings 0..11 + lk/sq reset runs + u_l0/u_l1 reset pads' if b == 'lk' else 'sq<->vc landings 12..20 + vc reset run + sq copies + u_l2 reset pad'}"
                 f", regrouped verbatim by tools/s81_dv/seq_three_roots_1021/build_bands_b1.py; two local CTS roots over a {388.8} x {c['h'][v]} um band. "
                 "No register, edge, reset depth or die port changed (program/landing lockstep benches PASS, missing-landing / K+1 / reset-run mutants caught)."
                 + (" FB: one 21.6-um row taller (lower pin/std density)." if v == "f" else "")),
             "job": {"owner": "Claude:STW-S81c-COLLA2-VP", "branch": "claude/s81-seq-b1-1022", "tag": name,
                     "purpose": f"seq (B) hardened landing band {b} ({'MAIN' if v == 'm' else 'FB'}) for dsdv_seq_host_b1m/b1f",
                     "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}",
                     "extra_paths": base["job"]["extra_paths"] + ["results/arch/seq_b1_bands_1022"],
                     "benches": [dict(x) for x in BENCH]}}
        d = ROOT / "physical/ref_tile" / name; d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(name, {k: len(v2) for k, v2 in pins.items()}, {k: (len(v2["inputs"]), len(v2["outputs"])) for k, v2 in doms.items()})
