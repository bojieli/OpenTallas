#!/usr/bin/env python3
"""HBM-HC7-BANK 10-20 (H.STA.BLK.17): lane-row regional-root HC ring bank kits (successors of the rc3 kits).

rc3 --cts gates (10-20, ot-epyc9) FAILED at CTS on the 0dq clock rule:
  cb_rc3  glue root clk pin-flop spread 354.9 ps TT (2,398 boundary of 5,221 sinks; avg sink wire 1,301 um, depth 15..17)
  b0_rc3  glue root clk pin-flop spread 674.3 ps TT (4,418 boundary of 7,241 sinks, incl. the 2 x 2,049 exit relay)
Placement evidence (cb_rc3 3_place.odb, unanchored): CPI sum flops c_s beside their own lane leaves (x 350..632, all
heights), CPO sum flops between each row and the out face, SRAM capture wdat / xdat and lane enables beside their row,
landing / write port in the W-S corner (x <= 383, y <= 349).  One glue root per face therefore spanned the whole
777 x 734 tile around 12 SRAMs.

Successor (structural, 0 added edges; RTL ot_hbm_hc_bankrc_static.sv _rr / _rh tops): every glue root covers one
compact region --
  clk        in-face landing / write port / reset relays / CPI scalars (landing + control pin flops ANCHORED at the
             in face: OT_OFLOP_PORT_RE)
  clk_c      stage control;  clk_o  CPO scalars (anchored at the out face)
  clk_r<r>   lane row r: CPI sums of leaves 2r / 2r+1 + SRAM read capture + lane enables
  clk_q<r>   lane row r: CPO sums of leaves 2r / 2r+1
  b0: clk_s0 / clk_s1 exit relay stage 0 (s_i face) / stage 1 (s_o face)
  _rr = 4 row roots each (primary), _rh = 2 half-tile roots each (parallel fallback, different partition).
The 2,048-bit chain flops stay UNANCHORED: anchored at the faces, the W face -> col-1 leaf (x 604.8) and the row-3 leaf ->
S face hops would be ~605 / ~562 um single-cycle wires (> 405 reach) unless a relay edge is added.
Usage: python3 tools/ref_tile/specs_hbm_b_rtl2_1017/hc7bank_rr.py  (writes physical/ref_tile/hbm_hcq_bank_{cb,b0}_{rr,rh}/spec.json)
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("hcbank6_rc", HERE / "hcbank6_rc.py")
H6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H6)

RT = H6.RT
WIT = H6.WIT
BRANCH = "claude/hcbank6-bank-1020"
XDEF = "+define+HC_DRLY=2 +define+HC_XRLY=0 +define+HC_BANK_RC"
# landing / control scalar pins: their single pin flop is anchored at its face (the 2,048-bit chains are not)
PORT_RE = r"^(xb_d|wv|xv|j|wa|wfault|d_v|d_ss|d_nv|d_wa|d_xa|o_v|o_ss|o_nv|o_wa|o_xa)(\[|\Z)"


def bench(tag, define):
    x = f"{XDEF} +define+{define}"
    b = []
    for m, nm, note in ((0, "hc_ring_rc_exact", None), (1, "hc_ring_rc_mut1", "bank 3 (rc corner tile) weight slice rotated"),
                        (5, "hc_ring_rc_mut5", "bank 3 landing kept copy 5 writes the next hold slot")):
        e = {"name": nm, "cmd": f"HC_XDEF='{x}' bash rtl/test/run_hbm_hc_eng4_ring.sh {{RUN}}/bench/m{m} {m}",
             "threads": 16, "peak_ram_gb": 64, "needs": ["verilator"]}
        if m == 0:
            e.update(expect="pass", pass_regex="^HC_RING_LOCKSTEP MUT=0 rc=0",
                     min_count_regex="HC_ENG_DONE mode=0 npos=1 mixes=(\\d+) mixbad=0")
        else:
            e.update(expect="fail", pass_regex=f"^HC_RING_LOCKSTEP MUT={m} rc=0", fail_regex="HC_ENG FAIL", note=note,
                     fail_witness=f"{WIT}/ring_{tag}_mut{m}.log")
        b.append(e)
    return b


def make(src_kit, name, top, rows, mirror, tag, define):
    s = json.loads((RT / src_kit / "spec.json").read_text())
    s["name"] = name
    s["top"] = top
    s["sources"] = [H6.RC_SRC] + [f for f in s["sources"] if not f.endswith(("ot_hbm_hc_bankq_static.sv", "ot_hbm_hc_bank_static.sv"))]
    s["children"], s["macros"] = H6.geometry(mirror)
    glue = ["clk", "clk_c", "clk_o"] + [f"clk_r{r}" for r in range(rows)] + [f"clk_q{r}" for r in range(rows)]
    if mirror:
        glue += ["clk_s0", "clk_s1"]
    s["clock"] = "hybrid_entries"
    s["clock_port"] = "clk"
    s["clock_ports"] = glue + [f"ck_l[{g}]" for g in range(8)] + [f"ck_w[{g}]" for g in range(8)] + [f"ck_x[{h}]" for h in range(4)]
    s["clock_cts_roots"] = glue
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "clk",
                          "why": "ROOT-RST: rst_n lands at the in face in 2 clk stages, then the RTL ot_rst_relay copies (bankrc u_rst / u_rst_b)"}
    pins = s["pins"]
    outf = "N" if mirror else "S"
    for f in list(pins):
        pins[f] = [p for p in pins[f] if p not in ("clk_o", "clk_c")]
    pins[outf] = pins[outf] + ["clk_o"]
    anyp = ["clk_c"] + [f"clk_r{r}" for r in range(rows)] + [f"clk_q{r}" for r in range(rows)] + ["ck_l", "ck_w", "ck_x"]
    if mirror:
        pins["S"] = pins["S"] + ["clk_s0"]
        pins["E"] = pins["E"] + ["clk_s1"]
    pins["ANY"] = anyp
    s["io_flop_at_pins"] = {"cols": 4, "allow_none": True}
    ov = dict(s.get("orfs_vars", {}))
    ov["OT_OFLOP_PORT_RE"] = PORT_RE
    s["orfs_vars"] = ov
    s.pop("slot_change_request", None)
    part = (f"{rows} lane-row" if rows == 4 else f"{rows} half-tile") + " regional roots"
    s["slot_change_request"] = (
        "HC ring bank 777.6 x 734.4 (= cb_s1 / b0_s1 slot request); master ports + clock entries "
        f"({', '.join(glue)} glue roots, ck_l[7:0] lanes, ck_w[7:0] / ck_x[3:0] raw SRAM clocks): die clock forest "
        "delivers each entry at phi - R (HBM-HC7-BANK 10-20)")
    s["structural_change"] = (
        f"HBM-HC7-BANK 10-20 successor of hbm_hcq_bank_{'b0' if mirror else 'cb'}_rc3 (its --cts gate FAILED at CTS: glue "
        f"root clk pin-flop spread {'674.3 ps TT, 4,418 boundary of 7,241 sinks incl. the 2 x 2,049 exit relay' if mirror else '354.9 ps TT, 2,398 boundary of 5,221 sinks, avg sink wire 1,301 um'}; "
        "one root per face spanned the whole tile around 12 SRAMs).  Glue clock partition from the cb_rc3 placement: "
        f"{part} (clk_r: CPI sums + SRAM capture + lane enables of the row; clk_q: CPO sums of the row), clk in-face "
        "landing / write port / CPI scalars, clk_c stage control, clk_o CPO scalars"
        + (", clk_s0 / clk_s1 exit relay stage per face" if mirror else "")
        + "; landing / control scalar pin flops anchored at their faces (OT_OFLOP_PORT_RE), 2,048-bit chain flops "
        "unanchored (anchored they would make ~605 / ~562 um single-cycle hops to the far leaves).  RTL "
        "ot_hbm_hc_bankrc_static.sv: same function, 0 added edges (ring lockstep 5.050 PASS + MUT 1/5 FAIL witnesses); "
        "geometry / pins / FAN32 as the rc3 kit.  Die pin plan / HCRING joint ranges unchanged.")
    s["reroute_reason"] = {"kind": "structural",
                           "failed_job": f"ref_gate hbm_hcq_bank_{'b0' if mirror else 'cb'}_rc3 10-20 (CTS: 0dq glue-root pin-flop spread)",
                           "why": "regional glue clock roots per lane row / face + anchored face scalars (see structural_change)"}
    j = s["job"]
    j["owner"] = "Claude:LEAD5-HBM/HBM-HC7-BANK"
    j["branch"] = BRANCH
    j["tag"] = tag
    j["purpose"] = f"HC ring bank {name}: {part} successor of the rc3 kit (hybrid entries, FAN32, sized SRAM channels)"
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    ep = [p for p in j["extra_paths"] if p not in ("rtl/test/tb_hbm_hc_eng4_static_hier.vlt", "rtl/test/tb_hbm_hc_eng4_static_hier_rc.vlt", WIT)]
    j["extra_paths"] = ep + ["rtl/test/tb_hbm_hc_eng4_static_hier.vlt", "rtl/test/tb_hbm_hc_eng4_static_hier_rc.vlt", WIT]
    j["benches"] = bench("rr" if rows == 4 else "rh", define)
    d = RT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")


if __name__ == "__main__":
    make("hbm_hcq_bank_cb_s1", "hbm_hcq_bank_cb_rr", "ot_hbm_hc_bankq_rr_static", 4, False, "rr", "HC_BANK_RR")
    make("hbm_hcq_bank_b0_s1", "hbm_hcq_bank_b0_rr", "ot_hbm_hc_bankq0_rr_static", 4, True, "b0rr", "HC_BANK_RR")
    make("hbm_hcq_bank_cb_s1", "hbm_hcq_bank_cb_rh", "ot_hbm_hc_bankq_rh_static", 2, False, "rh", "HC_BANK_RH")
    make("hbm_hcq_bank_b0_s1", "hbm_hcq_bank_b0_rh", "ot_hbm_hc_bankq0_rh_static", 2, True, "b0rh", "HC_BANK_RH")
