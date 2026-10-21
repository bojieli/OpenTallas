#!/usr/bin/env python3
"""HBM-HCBANK9 10-21 (H.STA.BLK.17): _rw2 / _rw3 HC ring bank kits = the _rl kits (hc9bank_rl.py / hc9bank_e2.py) plus
per-SRAM write-data copies on per-SRAM-row roots clk_d0..3 (core WROW 1).

e2_rl --cts gate (10-21 00:05): clk_a (hold / asm_q / lb_q / wd_q, 2,817 internal sinks) pin-flop spread 283.5 ps TT:
the 1,024-b wd_q fed all 12 SRAMs, so its flops spread over the whole SRAM area.  Now each SRAM has its own kept 256-b
copy loaded from asm_q on the same edge (0 added), anchored beside its wd_in pins (existing OT_MPFLOP_PINS exact wd_in[0..255];
no shared hook change), clocked by its SRAM row's root clk_d<r>.
  _rw2: hold / asm_q / lb_q stay on clk_a (cb, e2)      _rw3: they move to clk (cb, e2; boundary-scoped in-face root)
  b0_rw2: hold / asm_q on clk (b0's in face is beside the SRAMs; b0_rp clk boundary 43.9 PASS)
Usage: python3 tools/ref_tile/specs_hbm_b_rtl2_1017/hc9bank_rw.py
"""
import json
from pathlib import Path

RT = Path(__file__).resolve().parents[3] / "physical" / "ref_tile"
WIT = "results/rtl/hbm_hc_ring_1020_bankrl"
ROW_Y0 = [43.2 + 172.8 * r for r in range(4)]


def rng(c):
    return [round(c - 0.5, 3), round(c + 0.5, 3)]


def benches(var):
    x = "+define+HC_DRLY=2 +define+HC_XRLY=0 +define+HC_BANK_RC +define+HC_BANK_RW2" + (
        " +define+HC_BANK_RW3" if var == "rw3" else "")
    run = "bash rtl/test/run_hbm_hc_eng4_ring.sh"
    return [
        {"name": f"hc_ring_{var}_exact", "cmd": f"HC_XDEF='{x}' {run} {{RUN}}/bench/m0 0", "needs": ["verilator"],
         "expect": "pass", "pass_regex": "^HC_RING_LOCKSTEP MUT=0 rc=0",
         "min_count_regex": r"HC_ENG_DONE mode=0 npos=1 mixes=(\d+) mixbad=0"},
        {"name": f"hc_ring_{var}_mut1", "cmd": f"HC_XDEF='{x}' {run} {{RUN}}/bench/m1 1", "needs": ["verilator"],
         "expect": "fail", "pass_regex": "^HC_RING_LOCKSTEP MUT=1 rc=0", "fail_regex": "HC_ENG FAIL",
         "note": f"bank 3 ({var} corner tile) weight slice rotated", "fail_witness": f"{WIT}/ring_{var}_mut1.log"},
        {"name": f"hc_ring_{var}_mut5", "cmd": f"HC_XDEF='{x}' {run} {{RUN}}/bench/m5 5", "needs": ["verilator"],
         "expect": "fail", "pass_regex": "^HC_RING_LOCKSTEP MUT=5 rc=0", "fail_regex": "HC_ENG FAIL",
         "note": "bank 3 landing kept copy 5 writes the next hold slot", "fail_witness": f"{WIT}/ring_{var}_mut5.log"},
    ]


def make(tile, var):
    src = f"hbm_hcq_bank_{tile}_rl"
    s = json.loads((RT / src / "spec.json").read_text())
    name = f"hbm_hcq_bank_{tile}_{var}"
    s["name"] = name
    s["top"] = {"b0": "ot_hbm_hc_bankq0_rw2_static", "cb": f"ot_hbm_hc_bankq_{var}_static",
                "e2": f"ot_hbm_hc_bankq_ft_{var}_static"}[tile]
    drop_a = tile == "b0" or var == "rw3"
    rs = [r for r in s["clock_cts_roots"] if not (drop_a and r == "clk_a")]
    i = rs.index("clk_e0")
    rs[i:i] = [f"clk_d{r}" for r in range(4)]
    s["clock_cts_roots"] = rs
    s["clock_ports"] = rs + [p for p in s["clock_ports"] if p.startswith("ck_")]
    face = {"b0": "W", "cb": "E", "e2": "N"}[tile]
    pins = s["pins"]
    for f in pins:
        pins[f] = [p for p in pins[f] if not (drop_a and p == "clk_a")]
    pins[face] = pins[face] + [f"clk_d{r}" for r in range(4)]
    pr = s["pin_ranges"]
    if drop_a:
        pr.pop("clk_a", None)
    for r in range(4):
        # b0 / cb: on the free side face at the SRAM row line (between clk_e and clk_q); e2: N face above the SRAMs
        pr[f"clk_d{r}"] = rng(ROW_Y0[r] + 69.12 - 24.0) if tile != "e2" else rng(220.0 + 12.0 * r)
    io = dict(s["io_flop_at_pins"])
    io.pop("macro_pins", None)
    s["pin_hook_before_flops"] = list(s.get("pin_hook_before_flops", [])) + [f"physical/ref_tile/{name}/write_pin_names.tcl"]
    s["io_flop_at_pins"] = io
    s["slot_change_request"] = s["slot_change_request"].split(" (")[0] + " (" + ", ".join(rs) + \
        " glue roots, ck_l[7:0], ck_w[7:0], ck_x[3:0]): die clock forest delivers each entry at phi - R"
    s["structural_change"] = (
        f"HBM-HCBANK9 10-21 successor of {src} (e2_rl --cts gate: clk_a write mass 283.5 ps TT over 2,817 sinks, the "
        "1,024-b wd_q feeding all 12 SRAMs).  One kept 256-b write-data copy per SRAM loaded from asm_q on the same edge, "
        "anchored beside its wd_in pins, clocked per SRAM row (clk_d0..3); hold / asm_q / lb_q on " +
        ("clk" if drop_a else "clk_a") + ".  Otherwise = " + src + " (one root per compact anchored register mass). "
        "0 added edges.")
    s["reroute_reason"] = {"kind": "structural", "failed_job": "ref_gate hbm_hcq_bank_e2_rl 10-21 (clk_a spread 283.5 ps TT)",
                           "why": "per-SRAM write-data copies on per-row roots (HBM-HCBANK9)"}
    j = s["job"]
    j["purpose"] = f"HC ring bank {name}: per-mass anchored roots + per-SRAM write-data copies ({var})"
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    j["benches"] = benches(var)
    d = RT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "write_pin_names.tcl").write_text('# HC bank rw2: use existing exact macro-pin anchors, without changing shared helpers.\nset ot_hcb_wdpins {}\nfor {set ot_hcb_bit 0} {$ot_hcb_bit < 256} {incr ot_hcb_bit} {\n  lappend ot_hcb_wdpins [format {wd_in[%d]} $ot_hcb_bit]\n}\nset ::env(OT_MPFLOP_PINS) [join $ot_hcb_wdpins ,]\nset ::env(OT_MPFLOP_GAP) 5.4\n')
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json", len(rs), "roots")


if __name__ == "__main__":
    make("b0", "rw2")
    for t in ("cb", "e2"):
        make(t, "rw2")
