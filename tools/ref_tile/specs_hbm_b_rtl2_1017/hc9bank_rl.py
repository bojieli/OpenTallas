#!/usr/bin/env python3
"""HBM-HCBANK9 10-20 (H.STA.BLK.17): HC ring bank kits with ONE clock root per compact register mass.

_rp / _rw --cts gates (10-20, ot-epyc9) FAILED:
  b0_rp  clk_r0 pin-flop spread 150.2 ps TT (all_internal_only, 800 sinks, insertion 419 ps)
  cb_rw  clk boundary spread 136.5 ps TT (349 of 3,172 sinks, insertion 796 ps)
3_place.odb evidence (sink dump per root):
  b0 clk_r0 = wd capture 512 (x 361-429, beside the SRAM pair) + xd capture 256 (x 235-425) + lane enables 32
  (x 39-212, beside the leaves): three separated clusters on one tree.  clk_q0 (CPO sums, unanchored) spread
  y 150-700 along the 550 um leaf -> out-face path.  cb_rw clk = W-face pin flops (x 3-8) + 2.8 k write-mass flops
  (hold / asm_q / wd_q, x 307-773): one tree across the tile.
Structural change (RTL tops ot_hbm_hc_bankq*_rl_static / _rm_static, 0 added edges):
  * every glue root clocks ONE register mass, and the kit anchors that mass beside the pins it serves
    (io_flop_at_pins knobs already in the flow):
      macro_out_pins rd_out -> wd / xd read-capture flops beside each SRAM's rd_out edge   (clk_w<r> / clk_x<r>)
      macro_out_pins y      -> CPO sum flops beside each leaf's y face                       (clk_q<r>)
      macro_pins lv_i,ss_i  -> lane-enable flops beside each leaf's lv_i / ss_i pins          (clk_e<r>)
      sum_in port anchor    -> cb CPI sum flops at the in face                               (clk_i<r>)
      clk_a (cb, b0_rl)     -> write mass (hold / asm_q / lb_q / wd_q) off the in-face pin root clk
  * _rm (parallel fallback): wd + xd capture of one SRAM row on one root clk_r<r>; b0_rm keeps the write mass on clk
    (b0_rp clk boundary spread 43.9 ps PASS with it).
  * root pins on the free face (b0 W, cb E) at the region's row line.
Usage: python3 tools/ref_tile/specs_hbm_b_rtl2_1017/hc9bank_rl.py  (writes physical/ref_tile/hbm_hcq_bank_{b0,cb}_{rl,rm}/)
"""
import json
from pathlib import Path

RT = Path(__file__).resolve().parents[3] / "physical" / "ref_tile"
BRANCH = "claude/hcbank9-1020"
WIT = "results/rtl/hbm_hc_ring_1020_bankrl"
ROW_Y0 = [43.2 + 172.8 * r for r in range(4)]
XDEF = "+define+HC_DRLY=2 +define+HC_XRLY=0 +define+HC_BANK_RC +define+HC_BANK_{V}"


def rng(c):
    return [round(c - 0.5, 3), round(c + 0.5, 3)]


def roots(var, b0):
    r = ["clk"]
    if var == "rl" or not b0:
        r.append("clk_a")
    r += ["clk_c", "clk_o"]
    if var == "rl":
        r += [f"clk_w{i}" for i in range(4)] + [f"clk_x{i}" for i in range(4)]
    else:
        r += [f"clk_r{i}" for i in range(4)]
    r += [f"clk_e{i}" for i in range(4)]
    if not b0:
        r += [f"clk_i{i}" for i in range(4)]
    r += [f"clk_q{i}" for i in range(4)]
    if b0:
        r += ["clk_s0", "clk_s1"]
    return r


def benches(var):
    v = var.upper()
    x = XDEF.format(V=v)
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


def make(src, name, var, b0):
    s = json.loads((RT / src / "spec.json").read_text())
    s["name"] = name
    s["top"] = ("ot_hbm_hc_bankq0_%s_static" if b0 else "ot_hbm_hc_bankq_%s_static") % var
    face = "W" if b0 else "E"
    old = ["clk_c"] + [f"clk_r{r}" for r in range(4)] + [f"clk_q{r}" for r in range(4)]
    pins = s["pins"]
    for f in pins:
        pins[f] = [p for p in pins[f] if p not in old]
    rs = roots(var, b0)
    placed = [p for p in rs if p not in ("clk", "clk_o", "clk_s0", "clk_s1")]
    pins[face] = pins.get(face, []) + placed
    pr = s.setdefault("pin_ranges", {})
    for p in old:
        pr.pop(p, None)
    for r in range(4):
        yc = ROW_Y0[r] + 69.12          # leaf / SRAM-pair row centre
        pr[f"clk_e{r}"] = rng(yc - 36.0)
        pr[f"clk_q{r}"] = rng(yc - 12.0)
        if var == "rl":
            pr[f"clk_w{r}"] = rng(yc + 12.0)
            pr[f"clk_x{r}"] = rng(yc + 36.0)
        else:
            pr[f"clk_r{r}"] = rng(yc + 24.0)
        if not b0:
            pr[f"clk_i{r}"] = rng(yc + 60.0)
    pr["clk_c"] = rng(367.2 + 8.0)
    if "clk_a" in rs:
        pr["clk_a"] = rng(367.2 - 8.0)
    s["clock_cts_roots"] = rs
    ent = [p for p in s["clock_ports"] if p.startswith("ck_")]
    s["clock_ports"] = rs + ent
    io = dict(s.get("io_flop_at_pins") or {})
    io["macro_out_pins"] = ["rd_out", "y"]
    io["macro_pins"] = ["lv_i", "ss_i"]
    s["io_flop_at_pins"] = io
    if not b0:
        ov = dict(s.get("orfs_vars", {}))
        ov["OT_OFLOP_PORT_RE"] = ov["OT_OFLOP_PORT_RE"].replace("^(xb_d|", "^(sum_in|xb_d|")
        s["orfs_vars"] = ov
    s["slot_change_request"] = (
        "HC ring bank 777.6 x 734.4 (= cb_s1 / b0_s1 slot request); master ports + clock entries (" + ", ".join(rs) +
        " glue roots, ck_l[7:0] lanes, ck_w[7:0] / ck_x[3:0] raw SRAM clocks): die clock forest delivers each entry at "
        "phi - R (H-D4G / HBM-DIE6)")
    s["structural_change"] = (
        f"HBM-HCBANK9 10-20 successor of {src} (--cts gate FAILED: b0_rp clk_r0 150.2 ps TT over 3 separated clusters; "
        "cb_rw clk 136.5 ps TT with the 2.8 k write mass 300-770 um from its W-face pin flops).  One glue root per "
        "compact register mass, the mass anchored beside the pins it serves: SRAM read capture beside rd_out "
        "(clk_w/clk_x" + ("" if var == "rl" else " -> clk_r per SRAM row") + "), CPO sums beside the leaf y face "
        "(clk_q), lane enables beside lv_i / ss_i (clk_e)" + ("" if b0 else ", CPI sums at the in face (clk_i)") +
        (", write mass on clk_a" if "clk_a" in rs else ", write mass on clk (b0_rp clk boundary 43.9 PASS)") +
        ".  0 added edges.")
    s["reroute_reason"] = {"kind": "structural", "failed_job": f"ref_gate {src} 10-20 (CTS pin-flop spread > 80 TT)",
                           "why": "one clock root per compact, pin-anchored register mass (HBM-HCBANK9)"}
    j = s["job"]
    j["owner"] = "Claude:DRIVE-HBM/HBM-HCBANK9"
    j["branch"] = BRANCH
    j["purpose"] = f"HC ring bank {name}: one clock root per anchored register mass ({var})"
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    if WIT not in j["extra_paths"]:
        j["extra_paths"].append(WIT)
    j["benches"] = benches(var)
    d = RT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json", len(rs), "roots")


if __name__ == "__main__":
    for var in ("rl", "rm"):
        make("hbm_hcq_bank_b0_rp", f"hbm_hcq_bank_b0_{var}", var, True)
        make("hbm_hcq_bank_cb_rw", f"hbm_hcq_bank_cb_{var}", var, False)
