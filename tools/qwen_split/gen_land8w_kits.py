#!/usr/bin/env python3
"""QW-LANDW 10-19: writes physical/ref_tile/<kit>/spec.json for the WIDE D8 hop-0 landing masters
(physical/qwen_fwd_lane/qfd_land8w_masters.sv, tools/qwen_split/gen_land8w_masters.py).  Then
`python3 tools/ref_tile/ref_tile.py gen <spec>` per kit.  Pattern = tools/qwen_split/gen_land8_kits.py (QW-LAND8)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_land8w_masters import masters, MACRO_AT  # noqa: E402

MACRO = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1"
SRC = ["rtl/qwen_split/qfd_land8.sv", "rtl/qwen_split/qfd_land8s.sv", "rtl/hdc/ot_hdc_cg.sv",
       f"{MACRO}/ot_sram_1r1w2c_32x64_m1_bb.v", "physical/qwen_fwd_lane/qfd_land8w_masters.sv"]
WIT = "results/arch/qw_landw_1019/bench"
MUTS = ["sel", "naive", "vld", "encomb", "k3", "wsel", "rsel"]
CHK_FLOP = ("SAFE checklist (owner 10-19): 1 pins registered by construction (a -> bank flops, en -> en_s0, rs -> rs0, "
            "k -> k_q, b / fault = flops; reset 2 stages per side) | 2 reach: tile < 50 um | 3 fanout: kept 16-b regions, "
            "selects <= 16 data loads, en_s0 / rs0 <= 10 loads | 4 depth: ring -> o = 8:1 AND-OR, no in->out path | "
            "5 storage: D8 flop ring 8 x W = 856 / 928 b per slot set (< 2 kb: flop class) | 6 floorplan: no macros, "
            "outline from the estimated synthesis area (QW-LAND8 W10/W32 fit) at ~50 % util, square | 7 clock: two roots "
            "(ck, ck_s), ICG enable = en_icg.Q only (main) / no ICG (fallback n), ring -> o directly timed (land8_clocks.tcl), "
            "io_hold_margin 0.03 | 8 schedule: static, K = (L + G - R0 - 1) mod 16 (the D8 calendar, QW-GEN3 notice)")
CHK_SRAM = ("SAFE checklist (owner 10-19): 1 pins registered (a -> a_q pin register before the macro write, en -> en_s0 "
            "-> en_icg, rs -> rs0, k -> k_q, b = output register after the registered macro read, fault flop) | 2 reach: "
            "tile 98 x 171 um | 3 fanout: per-bank kept control copies (en_q, wp, wce_q, rs1, rce_q, ra_q, use x2 <= 32 "
            "loads) in a non-parameterised kept bank module (no paramod merge) | 4 depth: macro rd_out (~245 ps) -> AND "
            "-> o, no in->out path | 5 storage: lane record 453/520/548 b x 8 slots = 3.6..4.4 kb -> dual-clock SRAM "
            "macros (ot_sram_1r1w2c_32x64_m1, 3 per slice tile, lane = 3 slice tiles) | 6 floorplan: 3 macros on the "
            "43.2-um lattice (43.2, 43.2 / 86.4 / 129.6), 25.9-um N-S channels, >= 23 um from the pin faces, macro pin "
            "faces 5.95 pins/um (the CLOSED sram_escape64_1019 coupon), tile pin faces ~1.1 pins/um, aspect 1.74, one "
            "std band; 3 macros (< 4: no parent fill rule) | 7 clock: two roots, ICG enable = en_icg.Q only (main) / no "
            "ICG (fallback sn), vld -> use crossing timed by land8_clocks.tcl, macro write->read age by the calendar "
            "(no wclk->rd_out arc), io_hold_margin 0.03 | 8 schedule: static, K = (L + G - R0 - 2) mod 16, age "
            "(L - 3) T + phi in [1.25 T, 4.125 T]: +2 receiver edges vs the flop D8 (priced, QW-GEN3 notice)")


def spec(top, w, icg, core, fw, fh):
    name = top.lower().replace("qfd_", "qfwd_")
    sram = core == "ot_qfd_land8s"
    variant = ("hop-0 ICG on ck_s with the registered enable (main)" if icg else "no hop-0 clock gate (fallback)")
    kind = "sram" if sram else "flop"
    benches = [{
        "name": "lint",
        "cmd": ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; " + top + " u_top (); endmodule' > "
                "{RUN}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "
                "-Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv "
                + " ".join(SRC) + " && echo lint-ok"),
        "expect": "pass", "threads": 1, "peak_ram_gb": 4, "needs": ["verilator"]}, {
        "name": "land8w_exact",
        "cmd": f"bash tools/qwen_split/bench_land8w.sh pass {{RUN}}/b_pass {top} {w} {kind}",
        "expect": "pass", "pass_regex": "LAND8_BENCH_ALL PASS", "threads": 2, "peak_ram_gb": 6,
        "needs": ["verilator"], "pass_witness": f"{WIT}/{top}_pass.log"}]
    for m in MUTS:
        benches.append({
            "name": f"{m}_mutant",
            "cmd": f"bash tools/qwen_split/bench_land8w.sh {m} {{RUN}}/b_{m} {top} {w} {kind}",
            "expect": "fail", "fail_regex": "LAND8_BENCH_ALL FAIL", "fail_witness": f"{WIT}/{top}_{m}.log",
            "threads": 2, "peak_ram_gb": 6, "needs": ["verilator"]})
    route = {"pd": 0.45, "threads": 2, "peak_ram_gb": 6, "pin_h": "M4", "pin_v": "M3 M5", "m5_pg_pitch": 2.7,
             "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03, "macro_halo_um": 5.4}
    macros = []
    if sram:
        route.update({"pd": 0.5, "threads": 4, "peak_ram_gb": 16, "macro_halo_um": 2.16, "macro_halo_x_um": 10.8,
                      "pin_min_tracks": 3})
        macros = [{"view": MACRO, "count": 1, "at": list(xy)} for xy in MACRO_AT]
    what = (f"D8 SRAM record slice (3 x 64-b dual-clock SRAM banks, pin register before the write, registered read + "
            f"output register; lanes 453 = 3 x 151, 520 = 174 + 2 x 173, 548 = 2 x 183 + 182)" if sram else
            "D8 flop ring (8 slots, wc/rc mod 16, four K straps, kept 16-bit regions, registered one-hot read selects)")
    return name, {
        "name": name, "top": top, "kind": "tile", "sources": SRC, "params": {}, "clock_port": "ck",
        "reset_ports": ["rs"],
        "reset_landing": {"enable": False, "reason": (
            "the RTL lands it: rs -> u_land.rs0 -> kept rs1 copies (2 registered stages on ck, async assert); the source "
            "reset en -> u_land.en_s0 -> en_icg / en_qm / en_q copies (2 stages on ck_s); both release latencies are in "
            "the die strap K")},
        "outline": {"w": fw, "h": fh, "exact": True}, "layer_cap": "M5",
        "pins": {"E": ["a"], "W": ["b"],
                 "N": ["ck_s", "en", "ck", "rs", "k0", "k1", "k2", "k3", "tie_hi", "tie_lo", "fault"]},
        "macros": macros, "children": [], "inter": ["*"], "refglob": "*u_land.rc*",
        "io_budget": {"in": 0.2, "out": 0.2}, "recipe": 4, "hold_budget": "die", "inhold": False, "outhold": False,
        "io_flop_at_pins": {"cols": 4, "allow_none": True}, "keep_pin_regs": True, "forwarded_clock": False,
        "pin_regs": {"enable": False, "reason": (
            "registered by construction: every input pin lands on one flop stage (a -> " +
            ("the a_q pin register of each SRAM bank" if sram else "the 8 ring bank flops") +
            ", en -> en_s0, rs -> rs0, k -> k_q) and every output is a flop (o, fault); a flow pin register would add a "
            "stage the die calendar does not price (the landh0 opt-out, OWNER RULE 19:50)")},
        "sdc_extra": ["physical/qwen_fwd_lane/land8_clocks.tcl"],
        "boundary_tcl": ["physical/qwen_fwd_lane/land8_clocks.tcl"],
        "route": route,
        "structural_change": (
            f"QW-LANDW 10-19 (LEAD3-QW; Q.STA.LAND600.3 wide lanes, D8 contract 5a266752c, land8 pattern): new {w}-b "
            f"hop-0 landing master {top}, {variant}: {what}; en -> 2 registered stages before the ICG enable (no "
            f"combinational enable into the gate). New master, no closed view. {CHK_SRAM if sram else CHK_FLOP}"),
        "job": {"owner": "Claude:QW-LANDW", "branch": "claude/qw-landw-1019", "tag": "lw1",
                "purpose": f"Qwen compute die wide D8 hop-0 landing {top} ({w} b, {variant})",
                "benches": benches, "views_to": f"physical/ref_tile/{name}/views",
                "record_to": f"results/rtl/ref_tile/{name}",
                "extra_paths": ["physical/qwen_fwd_lane", "rtl/qwen_split/qfd_land8.sv", "rtl/qwen_split/qfd_land8s.sv",
                                "rtl/hdc", "tools/qwen_split", MACRO, WIT]}}


def main():
    for top, w, icg, core, fw, fh in masters():
        name, s = spec(top, w, icg, core, fw, fh)
        d = f"physical/ref_tile/{name}"
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/spec.json", "w") as f:
            json.dump(s, f, indent=1)
            f.write("\n")
        print(d)


if __name__ == "__main__":
    main()
