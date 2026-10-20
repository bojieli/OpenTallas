#!/usr/bin/env python3
"""QW-LAND8 10-19: writes physical/ref_tile/qfwd_landh0d8{,n}_<W>_ew_<WxH>/spec.json for the D8 hop-0 landing masters
(physical/qwen_fwd_lane/qfd_land8_masters.sv, tools/qwen_split/gen_land8_masters.py SIZES).  Then run
`python3 tools/ref_tile/ref_tile.py gen <spec>` per kit."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_land8_masters import SIZES  # noqa: E402

SRC = ["rtl/qwen_split/qfd_land8.sv", "rtl/hdc/ot_hdc_cg.sv", "physical/qwen_fwd_lane/qfd_land8_masters.sv"]
WIT = "results/arch/qw_land8_1019/bench"
MUTS = ["sel", "naive", "vld", "encomb", "k3", "wsel", "rsel"]
CHECK = ("SAFE checklist (owner 10-19): 1 pins registered by construction (a -> bank flops, en -> en_s0, rs -> rs0, "
         "k -> k_q, b / fault = flops; reset 2 stages per side) | 2 reach: tile < 30 um | 3 fanout: selects <= 16 data "
         "loads, en_s0 / rs0 drive <= 2 + regions copies | 4 depth: ring -> o = 8:1 AND-OR, no in->out path | "
         "5 storage: D8 direct FF ring <= 32 b (< 2 kb, hybrid MODEL dee8d6b3a FF class); wider lanes = SRAM record "
         "(INF.SRAM) | 6 floorplan: no macros, outline from the estimated synthesis area at ~45-55 % util, aspect <= 1.1 "
         "| 7 clock: two roots (ck, ck_s), ICG enable = en_icg.Q only (main) / no ICG (fallback n), ring -> o directly "
         "timed with the D8 envelope (land8_clocks.tcl), io_hold_margin 0.03 | 8 schedule: static, D8 K mod 16 four "
         "pins, en +2 / rs +2 release edges priced in K = (L + G - R0 - 1) mod 16 (QW-GEN3 notice)")


def spec(w, tag, fw, fh):
    top = f"qfd_landh0{tag}_{w}_EW_{round(fw)}x{round(fh)}"
    name = top.lower().replace("qfd_", "qfwd_")
    variant = "hop-0 ICG on ck_s with the registered enable (main)" if tag == "d8" else "no hop-0 clock gate (fallback)"
    benches = [{
        "name": "lint",
        "cmd": ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; " + top + " u_top (); endmodule' > "
                "{RUN}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "
                "-Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv "
                + " ".join(SRC) + " && echo lint-ok"),
        "expect": "pass", "threads": 1, "peak_ram_gb": 4, "needs": ["verilator"]}, {
        "name": "land8_exact",
        "cmd": f"bash tools/qwen_split/bench_land8.sh pass {{RUN}}/b_pass {top} {w}",
        "expect": "pass", "pass_regex": "LAND8_BENCH_ALL PASS", "threads": 2, "peak_ram_gb": 4,
        "needs": ["verilator"], "pass_witness": f"{WIT}/{top}_pass.log"}]
    for m in MUTS:
        benches.append({
            "name": f"{m}_mutant",
            "cmd": f"bash tools/qwen_split/bench_land8.sh {m} {{RUN}}/b_{m} {top} {w}",
            "expect": "fail", "fail_regex": "LAND8_BENCH_ALL FAIL", "fail_witness": f"{WIT}/{top}_{m}.log",
            "threads": 2, "peak_ram_gb": 4, "needs": ["verilator"]})
    return name, {
        "name": name, "top": top, "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
        "reset_ports": ["rs"],
        "reset_landing": {"enable": False, "reason": (
            "the RTL lands it: rs -> u_land.rs0 -> kept rs1 copies (2 registered stages on ck, async assert); the source "
            "reset en -> u_land.en_s0 -> en_icg / en_qm / region en_q (2 stages on ck_s); both release latencies are in "
            "the die strap K = (L + G - R0 - 1) mod 16")},
        "outline": {"w": fw, "h": fh, "exact": True}, "layer_cap": "M5",
        "pins": {"E": ["a"], "W": ["b"],
                 "N": ["ck_s", "en", "ck", "rs", "k0", "k1", "k2", "k3", "tie_hi", "tie_lo", "fault"]},
        "macros": [], "children": [], "inter": ["*"], "refglob": "*u_land.rc*",
        "io_budget": {"in": 0.2, "out": 0.2}, "recipe": 4, "hold_budget": "die", "inhold": False, "outhold": False,
        "io_flop_at_pins": {"cols": 4, "allow_none": True}, "keep_pin_regs": True, "forwarded_clock": False,
        "pin_regs": {"enable": False, "reason": (
            "registered by construction: every input pin lands on one flop stage (a -> the 8 ring bank flops, en -> "
            "en_s0, rs -> rs0, k -> k_q) and every output is a flop (o, fault); a flow pin register would add a stage "
            "the die calendar does not price (the landh0 opt-out, OWNER RULE 19:50)")},
        "sdc_extra": ["physical/qwen_fwd_lane/land8_clocks.tcl"],
        "boundary_tcl": ["physical/qwen_fwd_lane/land8_clocks.tcl"],
        "route": {"pd": 0.45, "threads": 2, "peak_ram_gb": 6, "pin_h": "M4", "pin_v": "M3 M5", "m5_pg_pitch": 2.7,
                  "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03, "macro_halo_um": 5.4},
        "structural_change": (
            f"QW-LAND8 10-19 (LEAD-QW 12:15: Q.STA.LAND600.3 = 8-slot D8 landing, contract 5a266752c; hybrid MODEL "
            f"dee8d6b3a FF-ring class): new {w}-b hop-0 landing master {top}, {variant}. D8 ring (8 slots, wc/rc mod "
            f"16, four K straps), en -> 2 registered stages before the ICG enable (no combinational enable into the "
            f"gate), kept 16-bit regions, registered one-hot read selects. New master, no closed view. {CHECK}"),
        "job": {"owner": "Claude:QW-LAND8", "branch": "claude/qw-land8-1019", "tag": "l8a",
                "purpose": f"Qwen compute die D8 hop-0 landing {top} ({w} b, {variant})",
                "benches": benches, "views_to": f"physical/ref_tile/{name}/views",
                "record_to": f"results/rtl/ref_tile/{name}",
                "extra_paths": ["physical/qwen_fwd_lane", "rtl/qwen_split/qfd_land8.sv", "rtl/hdc", "tools/qwen_split",
                                WIT]}}


def main():
    for w, (fw, fh) in SIZES.items():
        for tag in ("d8", "d8n"):
            name, s = spec(w, tag, fw, fh)
            d = f"physical/ref_tile/{name}"
            os.makedirs(d, exist_ok=True)
            json.dump(s, open(f"{d}/spec.json", "w"), indent=1)
            open(f"{d}/spec.json", "a").write("\n")
            print(d)


if __name__ == "__main__":
    main()
