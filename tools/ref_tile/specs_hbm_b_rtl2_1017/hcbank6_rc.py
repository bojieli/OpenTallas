#!/usr/bin/env python3
"""HBM-HCBANK6 10-20 (H.STA.BLK.17): regional-clock HC ring bank kits from the cb_s1 / b0_s1 SAFE kits.

cb_s1 --cts gate (10-19 16:48, ot-epyc4) FAILED: GATE_STALL in post-GRT hold repair after one balanced clk SPINE of
15,636 buffers over 10,737 sinks (8 hard lane leaves + 12 SRAM clock pins + 10.7 k glue flops): TT insertion
975..1271 ps (spread 296 ps); setup reg->macro -129.5 (wa_q -> x SRAM 600 um away), macro->reg -12.9 (row-3 leaf y ->
S-face CPO flop ~600 um); weight SRAM read faces (rd_out on the macro W face, R0) pointed AWAY from the lanes.

Successor (structural, 0 added edges; RTL ot_hbm_hc_bankrc_static.sv):
  clock   hybrid_entries cluster: glue CTS root(s) + one entry per hard lane leaf (ck_l[g]) + one raw-Liberty entry per
          SRAM (ck_w[g], ck_x[h]); the die delivers phi - R at each entry (neighbour-matched boundary), no spine.
          rc3 = three regional glue roots (clk in-face mass, clk_c stage + SRAM capture mass, clk_o out-face mass);
          rc  = one glue root clk (fallback).
  floorplan per lane row r (y0 = 43.2 + 172.8 r): x SRAM r MY at (43.2, y0) (write port 43 um from the in face, was
          600 um), weight pair 2r / 2r+1 MY at (172.8, y0) / (172.8, y0 + 70.512) (rd_out + address faces E, toward the
          lanes, across the 84.5 um pin channel), lane leaves 2r / 2r+1 at (432, y0) / (604.8, y0).  b0 = x-mirror
          (SRAMs R0 on the E side, dense faces W toward the lanes, leaves at 43.2 / 216).
  pins    die contract unchanged (cb_s1 / b0_s1 ranges and faces = HCRING joint plan); clock entries added on ANY face.
  FAN32   native32 census of the mapped netlist 0 violations (base bankq: 4 drivers > 32, max 512).
Usage: python3 tools/ref_tile/specs_hbm_b_rtl2_1017/hcbank6_rc.py   (writes physical/ref_tile/hbm_hcq_bank_{cb_rc3,cb_rc,b0_rc3}/spec.json)
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RT = ROOT / "physical/ref_tile"
LANES = "physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes"
WM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2"
XM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"
RC_SRC = "rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankrc_static.sv"
XDEF = "+define+HC_DRLY=2 +define+HC_XRLY=0 +define+HC_BANK_RC"
WIT = "results/rtl/hbm_hc_ring_1020_bankrc"
BRANCH = "claude/hcbank6-bank-1020"


def geometry(mirror):
    kids, macs = [], []
    for r in range(4):
        y0 = 43.2 + 172.8 * r
        if not mirror:
            xs, xw, xl, orient = 43.2, 172.8, (432.0, 604.8), "MY"
        else:
            xs, xw, xl, orient = 648.0, 432.0, (43.2, 216.0), "R0"
        for c in range(2):
            g = 2 * r + c
            kids.append({"view": LANES, "count": 1, "inst": f"*g_grp?{g}?.u_lg", "at": [xl[c], round(y0, 3)], "orient": "R0"})
        for c in range(2):
            g = 2 * r + c
            macs.append({"view": WM, "count": 1, "inst": f"*g_w?{g}?.u_m", "at": [xw, round(y0 + 70.512 * c, 3)],
                         "orient": orient, "at_exact": True,
                         "clock_entry": {"port": f"ck_w[{g}]", "pin": "clk", "reference": "raw_liberty_clock_pin"}})
        macs.append({"view": XM, "count": 1, "inst": f"*g_x?{r}?.u_m", "at": [xs, round(y0, 3)], "orient": orient,
                     "at_exact": True,
                     "clock_entry": {"port": f"ck_x[{r}]", "pin": "clk", "reference": "raw_liberty_clock_pin"}})
    return kids, macs


def bench(tag, extra=""):
    x = XDEF + extra
    return [
        {"name": "hc_ring_rc_exact", "cmd": f"HC_XDEF='{x}' bash rtl/test/run_hbm_hc_eng4_ring.sh {{RUN}}/bench/m0 0",
         "expect": "pass", "pass_regex": "^HC_RING_LOCKSTEP MUT=0 rc=0",
         "min_count_regex": "HC_ENG_DONE mode=0 npos=1 mixes=(\\d+) mixbad=0", "threads": 16, "peak_ram_gb": 64,
         "needs": ["verilator"]},
        {"name": "hc_ring_rc_mut1", "cmd": f"HC_XDEF='{x}' bash rtl/test/run_hbm_hc_eng4_ring.sh {{RUN}}/bench/m1 1",
         "expect": "fail", "pass_regex": "^HC_RING_LOCKSTEP MUT=1 rc=0", "fail_regex": "HC_ENG FAIL", "threads": 16,
         "peak_ram_gb": 64, "needs": ["verilator"], "note": "bank 3 (rc corner tile) weight slice rotated",
         "fail_witness": f"{WIT}/ring_{tag}_mut1.log"},
        {"name": "hc_ring_rc_mut5", "cmd": f"HC_XDEF='{x}' bash rtl/test/run_hbm_hc_eng4_ring.sh {{RUN}}/bench/m5 5",
         "expect": "fail", "pass_regex": "^HC_RING_LOCKSTEP MUT=5 rc=0", "fail_regex": "HC_ENG FAIL", "threads": 16,
         "peak_ram_gb": 64, "needs": ["verilator"], "note": "bank 3 landing kept copy 5 writes the next hold slot",
         "fail_witness": f"{WIT}/ring_{tag}_mut5.log"},
    ]


def make(src_kit, name, top, roots, mirror, anchor, tag, extra=""):
    s = json.loads((RT / src_kit / "spec.json").read_text())
    s = copy.deepcopy(s)
    s["name"] = name
    s["top"] = top
    s["sources"] = [RC_SRC] + [f for f in s["sources"] if not f.endswith(("ot_hbm_hc_bankq_static.sv", "ot_hbm_hc_bank_static.sv"))]
    s["children"], s["macros"] = geometry(mirror)
    ports = list(roots) + [f"ck_l[{g}]" for g in range(8)] + [f"ck_w[{g}]" for g in range(8)] + [f"ck_x[{h}]" for h in range(4)]
    s["clock"] = "hybrid_entries"
    s["clock_port"] = "clk"
    s["clock_ports"] = ports
    s["clock_cts_roots"] = list(roots)
    s["reset_landing"] = {"enable": True, "stages": 2, "clock": "clk",
                          "why": "ROOT-RST: rst_n lands at the in face in 2 clk stages, then the RTL ot_rst_relay copies (bankrc u_rst / u_rst_b)"}
    pins = s["pins"]
    if "clk_o" in roots:
        outf = "S" if not mirror else "N"
        pins[outf] = pins[outf] + ["clk_o"]
        pins["ANY"] = ["clk_c", "ck_l", "ck_w", "ck_x"]
    else:
        pins["ANY"] = ["ck_l", "ck_w", "ck_x"]
    if anchor:
        s["io_flop_at_pins"] = {"cols": 4, "allow_none": True}
    else:
        s["io_flop_at_pins"] = False
    s.pop("slot_change_request", None)
    s["slot_change_request"] = ("HC ring bank 777.6 x 734.4 (= cb_s1 / b0_s1 slot request); master ports + 20 clock entries "
                                f"({', '.join(roots)} glue roots, ck_l[7:0] lanes, ck_w[7:0] / ck_x[3:0] raw SRAM clocks): die "
                                "clock forest delivers each entry at phi - R (HBM-HCBANK6 10-20)")
    s["structural_change"] = (
        f"HBM-HCBANK6 10-20 regional-clock successor of {src_kit} (its --cts gate: GATE_STALL in post-GRT hold repair, "
        "one 15,636-buffer clk spine over 10,737 sinks, TT insertion 975..1271 ps = 296 ps spread; reg->macro -129.5 "
        "wa_q -> x SRAM 600 um; macro->reg -12.9 row-3 leaf y -> S-face CPO flop; weight SRAM rd_out faces pointed away "
        "from the lanes).  RTL ot_hbm_hc_bankrc_static.sv (0 added edges, ring lockstep 5.050 PASS + MUT 1/5 FAIL "
        "witnesses): hybrid_entries cluster -- glue CTS root(s) "
        f"{'/'.join(roots)} + ck_l[g] per hard lane leaf + raw-Liberty ck_w[g] / ck_x[h] per SRAM (no spine); FAN32 "
        "kept copies (beat landing x16, lane enables x4): mapped native32 census 0 > 32 (base 4, max 512).  Floorplan "
        + ("per lane row: x SRAM MY at x43.2 (write port 43 um from the in face), weight pair MY at x172.8 (rd_out / "
           "address face E toward the lanes over the 84.5 um channel), leaves x432 / x604.8"
           if not mirror else
           "x-mirror for b0 (inputs E): x SRAM R0 x648, weight pair R0 x432 (rd_out face W toward the lanes), leaves "
           "x43.2 / x216")
        + ("; CPI/CPO chain flops placed by the placer between face and leaf (no pin anchor) so no single-cycle wire "
           "exceeds the 405 um reach (row-3 leaf -> out face was ~600 um)" if not anchor else
           "; chain pin flops anchored at the faces (cb_s1 convention)")
        + ".  Die pin plan / HCRING joint ranges unchanged.")
    s["reroute_reason"] = {"kind": "structural", "failed_job": f"ref_gate {src_kit} 10-19 (GATE_STALL post-GRT hold repair)",
                           "why": "regional clock entries + SRAM orientation/placement + FAN32 (see structural_change)"}
    j = s["job"]
    j["owner"] = "Claude:LEAD4-HBM/HBM-HCBANK6"
    j["branch"] = BRANCH
    j["tag"] = tag
    j["purpose"] = f"HC ring bank {name}: regional-clock successor of {src_kit} (hybrid entries, FAN32, sized SRAM channels)"
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    ep = [p for p in j["extra_paths"] if p != "rtl/test/tb_hbm_hc_eng4_static_hier.vlt"]
    j["extra_paths"] = ep + ["rtl/test/tb_hbm_hc_eng4_static_hier.vlt", "rtl/test/tb_hbm_hc_eng4_static_hier_rc.vlt", WIT]
    j["benches"] = bench("rc3" if "RC3" in extra else "rc", extra)
    d = RT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print("wrote", d / "spec.json")


if __name__ == "__main__":
    make("hbm_hcq_bank_cb_s1", "hbm_hcq_bank_cb_rc3", "ot_hbm_hc_bankq_rc3_static", ["clk", "clk_c", "clk_o"], False, False,
         "rc3", " +define+HC_BANK_RC3")
    make("hbm_hcq_bank_cb_s1", "hbm_hcq_bank_cb_rc", "ot_hbm_hc_bankq_rc_static", ["clk"], False, True, "rc")
    make("hbm_hcq_bank_b0_s1", "hbm_hcq_bank_b0_rc3", "ot_hbm_hc_bankq0_rc3_static", ["clk", "clk_c", "clk_o"], True, False,
         "b0rc3", " +define+HC_BANK_RC3")
