#!/usr/bin/env python3
"""Place-and-route cases of the local K arbitration partition (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md).

At the adopted clock (0.92 ns, ASAP7) with 60 ps clock uncertainty, AW = 30 (full shape), through
tools/run_abi3_physical.py so every record has the physical.json schema, source pins and verdict.

  slice      ot_chip_v41x_karb_slice: one pseudo-channel in the proposal's 375 x 64 um study envelope.
             Stack-side h_*/r_* pins on the bottom edge inside the PC's PHY pin sub-window (20-195 um,
             matching ot_hbm3e_phy_v41x_aw30's PC pin span 20-142 um), bridge-side b_* pins on the top
             edge in the same span, the regional K port on the top edge at 200-370 um.
  region     ot_chip_v41x_karb_region: four PCs, 1500 x 64 um, per-PC pins as the slice; the K trunk
             request on the top edge in PC1's free span, the response in PC2's (the region centre).
  stack_ep   ot_chip_v41x_karb_stack_ep (NREG = 8), a compact block: K port on the top edge, the
             broadcast request on the bottom centre, regions 0-3 trunks bottom-left, 4-7 bottom-right.
  *_band     slice / region in the current floorplan band height (17.28 um) instead of 64 um.
  trunk_end / trunk_mid   the trunk cut at 11.4 mm (endpoint at the stack end) and 3.15 mm.
  trunk_far  rtl/chip/physical/ot_v41x_karb_trunk_cut.sv: the endpoint and the OUTERMOST region's K
             queues joined by the routed trunk.  The endpoint sits at the stack centre (6.0 mm along the
             12.0 mm PHY edge) and region 0's centre is at 0.75 mm, so the die is 5.4 mm x 64 um: K port
             at the right end, the region's slice-facing ports over the left 0.75 mm.

    python3 tools/v41x_karb_local_pnr.py slice --print
    OT_ORFS_NUM_CORES=8 python3 tools/v41x_karb_local_pnr.py slice --run --work ~/w2/pnr
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from v41x_die_pnr import PC_PIN_SPAN, PHY_PC_WINDOW_UM, ROW_UM, bits, karb_pc_pins, pin_regex  # noqa: E402

CLOCK_NS = 0.92
UNCERTAINTY_NS = 0.06
AW, TAGW, LENW, BEATW, DW = 30, 16, 4, 4, 256
ENV_H = 64.0
SLICE_VIEW = "physical/w18/ot_chip_v41x_karb_pslice"   # W18b --slice-view: hardened pslice abstract used by pregionh
PREGION_H = ENV_H                # W18b --pregion-h: the 216 um HBM service band leaves 145 um beside its 70.5 um SRAMs
K_SPAN = (200.0, 370.0)          # regional K port on the slice's top edge (v1 PHY window 375 um)
EPC_OUTER = 14                   # outermost region's credits, 2 * hops + 2 (12 mm PHY: 6 hops)
PROOT_HOPS = (6, 4, 3, 1, 1, 3, 4, 6)   # region 7 .. 0 trunk hops (12 mm PHY, 1 mm hops)
PROOT_H = 64.0
HOLD_NS = None                   # W18 --phy-e8p5: project SDC policy 25 ps hold uncertainty
SIGNOFF_ARGS: list = []          # W18 --signoff-1p2: harden at WC (SS libs), repair hold at WC and BC
BUFFER_HOOK = "physical/abi3/v41x_karb_repair_buffer_cap.tcl"
KARB = ["rtl/chip/ot_chip_v41x_karb_q2.sv", "rtl/chip/ot_chip_v41x_karb_q2r.sv", "rtl/chip/ot_chip_v41x_keep_dff.sv", "rtl/chip/ot_chip_v41x_stat_ctr32.sv", "rtl/chip/ot_chip_v41x_karb_qn.sv", "rtl/chip/ot_chip_v41x_karb_qh.sv"]


def common(top: str, sources: list[str], w: float, h: float, params: list[str] = (), density: float = 0.6):
    m = 4 * ROW_UM
    args = ["--view", "asap7", "--top", top]
    for s in sources:
        args += ["--source", s]
    for p in params:
        args += ["--param", p]
    if HOLD_NS is not None:
        args += ["--clock-uncertainty-hold-ns", f"{HOLD_NS:g}"]
    args += SIGNOFF_ARGS
    args += ["--clock-period-ns", f"{CLOCK_NS:g}", "--clock-uncertainty-ns", f"{UNCERTAINTY_NS:g}",
             "--io-delay-fraction", "0.2", "--stages", "synth,pnr",
             "--die-area", "0", "0", f"{w:g}", f"{h:g}", "--core-area", f"{m:g}", f"{m:g}", f"{w - m:g}", f"{h - m:g}",
             "--place-density", f"{density:g}"]
    for hook in ("PRE_CTS", "PRE_GLOBAL_ROUTE"):
        args += ["--step-tcl", f"{hook}={BUFFER_HOOK}"]
    return args


def span(x0: float, lo: float, hi: float) -> str:
    return f"{x0 + lo:g}-{x0 + hi:g}"


def slice_case(h: float = ENV_H, tag: str = "") -> dict:
    w = PHY_PC_WINDOW_UM
    regions = [
        r"^(h_v|h_rdy|h_we|h_wr_done|r_v|r_rdy)$|^(h_addr|h_len|h_tag|h_wdata|h_wstrb|r_tag|r_beat|r_data)\[\d+\]$"
        + f"=bottom:{span(0, *PC_PIN_SPAN)}",
        r"^(b_v|b_rdy|b_we|b_wr_done|b_rsp_v|b_rsp_rdy)$|^(b_addr|b_len|b_tag|b_wdata|b_wstrb|b_rsp_tag|b_rsp_beat|"
        r"b_rsp_data)\[\d+\]$" + f"=top:{span(0, *PC_PIN_SPAN)}",
        r"^(k_v|k_take|k_we|k_wr_done|k_rsp_v|k_rsp_rdy|b_grant|contend|clk|rst_n)$|^(k_addr|k_len|k_tag|k_wdata|"
        r"k_wstrb|k_rsp_tag|k_rsp_beat|k_rsp_data)\[\d+\]$" + f"=top:{K_SPAN[0]:g}-{K_SPAN[1]:g}",
    ]
    args = common("ot_chip_v41x_karb_slice", ["rtl/chip/ot_chip_v41x_karb_slice.sv"], w, h, [f"AW={AW}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": f"w2a_karb_slice_aw30{tag}",
            "output": f"results/physical_abi3/asap7/chip/v41x_karb_local/slice_aw30{tag}/physical.json",
            "floorplan": {"die_um": [w, h], "pc_pin_span_um": PC_PIN_SPAN, "k_span_um": list(K_SPAN)}}


def region_case(h: float = ENV_H, tag: str = "") -> dict:
    w = 4 * PHY_PC_WINDOW_UM
    regions = []
    for p in range(4):
        x0 = p * PHY_PC_WINDOW_UM
        regions.append(f"{pin_regex(karb_pc_pins(p, 'h', aw=AW))}=bottom:{span(x0, *PC_PIN_SPAN)}")
        regions.append(f"{pin_regex(karb_pc_pins(p, 'b', aw=AW))}=top:{span(x0, *PC_PIN_SPAN)}")
    regions.append(r"^(kq_v|kq_rdy|kq_we|clk|rst_n)$|^(kq_lpc|kq_addr|kq_len|kq_tag|kq_wdata|kq_wstrb)\[\d+\]$"
                   + f"=top:{span(PHY_PC_WINDOW_UM, *K_SPAN)}")
    regions.append(r"^(ks_v|ks_cr|k_wr_done)$|^(ks_tag|ks_beat|ks_data|b_grant_n|contend_n)\[\d+\]$"
                   + f"=top:{span(2 * PHY_PC_WINDOW_UM, *K_SPAN)}")
    srcs = ["rtl/chip/ot_chip_v41x_karb_region.sv", "rtl/chip/ot_chip_v41x_karb_region_kq.sv",
            "rtl/chip/ot_chip_v41x_karb_slice.sv", *KARB]
    args = common("ot_chip_v41x_karb_region", srcs, w, h, [f"AW={AW}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": f"w2a_karb_region_aw30{tag}",
            "output": f"results/physical_abi3/asap7/chip/v41x_karb_local/region_aw30{tag}/physical.json",
            "floorplan": {"die_um": [w, h], "pc_window_um": PHY_PC_WINDOW_UM, "pc_pin_span_um": PC_PIN_SPAN,
                          "trunk_request_top_um": [575, 745], "trunk_response_top_um": [950, 1120]}}


def stack_ep_case(w: float = 600.0) -> dict:
    h = ENV_H
    rw = TAGW + BEATW + DW
    pins_l, pins_r = [], []
    for g in range(8):
        pins = [f"rq_v[{g}]", f"rq_rdy[{g}]", f"rs_v[{g}]", f"rs_cr[{g}]", f"r_kwd[{g}]"]
        pins += bits("rs_d", rw, g * rw) + bits("r_bg", 3, g * 3) + bits("r_ct", 3, g * 3)
        (pins_l if g < 4 else pins_r).extend(pins)
    regions = [
        r"^(k_v|k_rdy|k_we|k_wr_done|k_rsp_v|k_rsp_rdy|clk|rst_n)$|^(k_addr|k_len|k_tag|k_wdata|k_wstrb|k_rsp_tag|"
        r"k_rsp_beat|k_rsp_data|k_grants|b_grants|contended)\[\d+\]$" + f"=top:{20:g}-{w - 20:g}",
        f"{pin_regex(pins_l)}=bottom:{10:g}-{w / 2 - 90:g}",
        r"^rq_we$|^(rq_lpc|rq_addr|rq_len|rq_tag|rq_wdata|rq_wstrb)\[\d+\]$" + f"=bottom:{w / 2 - 80:g}-{w / 2 + 80:g}",
        f"{pin_regex(pins_r)}=bottom:{w / 2 + 90:g}-{w - 10:g}",
    ]
    srcs = ["rtl/chip/ot_chip_v41x_karb_stack_ep.sv", *KARB]
    args = common("ot_chip_v41x_karb_stack_ep", srcs, w, h, [f"AW={AW}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": "w2a_karb_stack_ep_aw30",
            "output": "results/physical_abi3/asap7/chip/v41x_karb_local/stack_ep_aw30/physical.json",
            "floorplan": {"die_um": [w, h]}}


def trunk_case(length_um: float = 5400.0, tag: str = "_far") -> dict:
    w, h = length_um, ENV_H
    regions = [
        r"^(k_v|k_rdy|k_we|k_wr_done|k_rsp_v|k_rsp_rdy|clk|rst_n)$|^(k_addr|k_len|k_tag|k_wdata|k_wstrb|k_rsp_tag|"
        r"k_rsp_beat|k_rsp_data|k_grants|b_grants|contended)\[\d+\]$" + f"=top:{w - 260:g}-{w - 10:g}",
        r"^s_we$|^(s_kv|s_take|s_addr|s_len|s_tag|s_wdata|s_wstrb|s_kwd|s_bg|s_ct)\[\d+\]$" + f"=bottom:{20:g}-{730:g}",
        r"^(s_krv|s_krdy|s_rtag|s_rbeat|s_rdata)\[\d+\]$" + f"=top:{20:g}-{730:g}",
    ]
    srcs = ["rtl/chip/physical/ot_v41x_karb_trunk_cut.sv", "rtl/chip/ot_chip_v41x_karb_stack_ep.sv",
            "rtl/chip/ot_chip_v41x_karb_region_kq.sv", *KARB]
    args = common("ot_v41x_karb_trunk_cut", srcs, w, h)
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": f"w2a_karb_trunk{tag}",
            "output": f"results/physical_abi3/asap7/chip/v41x_karb_local/trunk{tag}/physical.json",
            "floorplan": {"die_um": [w, h], "k_port_top_um": [w - 260, w - 10], "region_side_um": [20, 730],
                          "trunk_length_um": w - 750 / 2 - 135}}


PIPE = ["rtl/chip/ot_chip_v41x_karb_pipe.sv", "rtl/chip/ot_chip_v41x_karb_slice.sv"]


def pslice_case() -> dict:
    c = slice_case()
    w, h = PHY_PC_WINDOW_UM, ENV_H
    regions = [
        r"^(h_v|h_rdy|h_we|h_wr_done|r_v|r_rdy)$|^(h_addr|h_len|h_tag|h_wdata|h_wstrb|r_tag|r_beat|r_data)\[\d+\]$"
        + f"=bottom:{span(0, *PC_PIN_SPAN)}",
        r"^(b_v|b_rdy|b_we|b_wr_done|b_rsp_v|b_rsp_rdy)$|^(b_addr|b_len|b_tag|b_wdata|b_wstrb|b_rsp_tag|b_rsp_beat|"
        r"b_rsp_data)\[\d+\]$" + f"=top:{span(0, *PC_PIN_SPAN)}",
        r"^(kin_v|kin_we|k_pop|k_wr_done|ks_v|ks_cr|b_grant|contend|clk|rst_n)$|^(kin_addr|kin_len|kin_tag|kin_wdata|"
        r"kin_wstrb|ks_tag|ks_beat|ks_data)\[\d+\]$" + f"=top:{K_SPAN[0]:g}-{K_SPAN[1]:g}",
    ]
    srcs = ["rtl/chip/ot_chip_v41x_karb_pslice.sv", "rtl/chip/ot_chip_v41x_karb_slice.sv", *KARB]
    args = common("ot_chip_v41x_karb_pslice", srcs, w, h, [f"AW={AW}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": "w2a_karb_pslice_aw30",
            "output": "results/physical_abi3/asap7/chip/v41x_karb_local/pslice_aw30/physical.json",
            "floorplan": {"die_um": [w, h], "pc_pin_span_um": PC_PIN_SPAN, "k_span_um": list(K_SPAN)}}


def pregion_case() -> dict:
    w, h = 4 * PHY_PC_WINDOW_UM, PREGION_H
    regions = []
    for p in range(4):
        x0 = p * PHY_PC_WINDOW_UM
        regions.append(f"{pin_regex(karb_pc_pins(p, 'h', aw=AW))}=bottom:{span(x0, *PC_PIN_SPAN)}")
        regions.append(f"{pin_regex(karb_pc_pins(p, 'b', aw=AW))}=top:{span(x0, *PC_PIN_SPAN)}")
    regions.append(r"^(t_v|t_we|clk|rst_n)$|^(t_lpc|t_addr|t_len|t_tag|t_wdata|t_wstrb|kcr)\[\d+\]$"
                   + f"=top:{span(PHY_PC_WINDOW_UM, *K_SPAN)}")
    regions.append(r"^(s_v|s_cr|k_wr_done)$|^(s_tag|s_beat|s_data|b_grant_n|contend_n)\[\d+\]$"
                   + f"=top:{span(2 * PHY_PC_WINDOW_UM, *K_SPAN)}")
    srcs = ["rtl/chip/ot_chip_v41x_karb_pregion.sv", "rtl/chip/ot_chip_v41x_karb_pslice.sv",
            "rtl/chip/ot_chip_v41x_karb_slice.sv", *KARB]
    # EPC: the outermost region's credits (2 * 6 + 2)
    args = common("ot_chip_v41x_karb_pregion", srcs, w, h, [f"AW={AW}", f"EPC={EPC_OUTER}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": "w2a_karb_pregion_aw30",
            "output": "results/physical_abi3/asap7/chip/v41x_karb_local/pregion_aw30/physical.json",
            "floorplan": {"die_um": [w, h], "pc_window_um": PHY_PC_WINDOW_UM, "pc_pin_span_um": PC_PIN_SPAN,
                          "tap_top_um": [575, 745], "send_top_um": [950, 1120]}}


def pregion_hier_case() -> dict:
    """W18b: the region built from four HARDENED pslice macros (floorplan -> hardened element -> replicate) at
    PREGION_H (>= 2 x the slice's 64 um: slices along the PHY edge, region glue above them)."""
    c = pregion_case()
    args = c["args"]
    srcs = [i + 1 for i, x in enumerate(args) if x == "--source"]
    keep = [args[i] for i in srcs if "pslice" not in args[i] and "karb_slice" not in args[i]]
    out, i = [], 0
    while i < len(args):
        if args[i] == "--source":
            i += 2
            continue
        out.append(args[i])
        i += 1
    for s in keep + [f"{SLICE_VIEW}/ot_chip_v41x_karb_pslice_bb.v"]:
        out += ["--source", s]
    out += ["--param", "HIER=1", "--macro-view", f"ot_chip_v41x_karb_pslice={SLICE_VIEW}",
            "--macro-place-halo", "1", "1", "--orfs-var", "MACRO_PLACEMENT_TCL=/src/physical/w18/karb_pregion_hier_place.tcl",
            "--orfs-var", "PDN_TCL=/src/physical/w18pdn/pdn_karb_hier.tcl"]
    c["args"] = out
    c["nickname"] = c["nickname"].replace("pregion", "pregionh")
    c["output"] = c["output"].replace("pregion_aw30", "pregionh_aw30")
    return c


def proot_case(w: float = 750.0) -> dict:
    h = PROOT_H
    rw = TAGW + BEATW + DW
    pins_l, pins_r = [], []
    for g in range(8):
        pins = [f"d_v[{g}]", f"s_v[{g}]", f"s_cr[{g}]", f"r_kwd[{g}]"] + bits("kcr", 4, 4 * g)
        pins += bits("s_d", rw, g * rw) + bits("r_bg", 3, g * 3) + bits("r_ct", 3, g * 3)
        (pins_l if g < 4 else pins_r).extend(pins)
    regions = [
        r"^(k_v|k_rdy|k_we|k_wr_done|k_rsp_v|k_rsp_rdy|clk|rst_n)$|^(k_addr|k_len|k_tag|k_wdata|k_wstrb|k_rsp_tag|"
        r"k_rsp_beat|k_rsp_data|k_grants|b_grants|contended)\[\d+\]$" + f"=top:{20:g}-{w - 20:g}",
        f"{pin_regex(pins_l)}=bottom:{10:g}-{w / 2 - 90:g}",
        r"^d_we$|^(d_lpc|d_addr|d_len|d_tag|d_wdata|d_wstrb)\[\d+\]$" + f"=bottom:{w / 2 - 80:g}-{w / 2 + 80:g}",
        f"{pin_regex(pins_r)}=bottom:{w / 2 + 90:g}-{w - 10:g}",
    ]
    srcs = ["rtl/chip/ot_chip_v41x_karb_proot.sv", *KARB]
    epcs = "".join(f"{2 * hp + 2:02x}" for hp in PROOT_HOPS)   # region 7 .. region 0
    args = common("ot_chip_v41x_karb_proot", srcs, w, h, [f"AW={AW}", f"EPCS=64'h{epcs}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": "w2a_karb_proot_aw30",
            "output": "results/physical_abi3/asap7/chip/v41x_karb_local/proot_aw30/physical.json",
            "floorplan": {"die_um": [w, h], "epcs_region7_to_0": epcs}}


def link_case(length_um: float = 1000.0) -> dict:
    w, h = length_um + 20.0, ENV_H
    regions = [r"^(d\[\d+\]|clk|rst_n)$=left", r"^q\[\d+\]$=right"]
    srcs = ["rtl/chip/physical/ot_v41x_karb_link_cut.sv", "rtl/chip/ot_chip_v41x_karb_pipe.sv"]
    args = common("ot_v41x_karb_link_cut", srcs, w, h)
    args[args.index("--io-delay-fraction") + 1] = "0.7"
    for r in regions:
        args += ["--pin-region", r]
    tag = f"{int(length_um)}"
    return {"args": args, "nickname": f"w2a_karb_link_{tag}",
            "output": f"results/physical_abi3/asap7/chip/v41x_karb_local/link_{tag}um/physical.json",
            "floorplan": {"die_um": [w, h], "segment_um": length_um, "io_delay_fraction": 0.7,
                          "note": "70% I/O delay pins both chain registers at their edge"}}


BAND_H = 17.28   # the current floorplan's KV/key/staging band height (12,000 x 17.2 um), on the row grid
CASES = {"slice": slice_case, "region": region_case, "stack_ep": stack_ep_case, "trunk_far": trunk_case,
         # the existing band budget instead of the proposal's 64 um study envelope
         "slice_band": lambda: slice_case(BAND_H, "_band"), "region_band": lambda: region_case(BAND_H, "_band"),
         # endpoint at the stack end (outermost region at 11.25 mm) and a mid-distance region (2.25 mm)
         "trunk_end": lambda: trunk_case(11400.0, "_end"), "trunk_mid": lambda: trunk_case(3150.0, "_mid"),
         # the pipelined partition (ot_chip_v41x_hbm_karb_pipe)
         "pslice": pslice_case, "pregion": pregion_case, "pregionh": pregion_hier_case, "proot": proot_case,
         "link600": lambda: link_case(600.0), "link450": lambda: link_case(450.0),
         "link900": lambda: link_case(900.0),
         "link_1000": link_case, "link_750": lambda: link_case(750.0), "link_1250": lambda: link_case(1250.0)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--work", type=Path, default=Path(os.environ.get("OT_V41PNR_WORK", "/home/ubuntu/w2/pnr")))
    ap.add_argument("--output")
    ap.add_argument("--stages")
    ap.add_argument("--density", type=float, help="override the global placement density")
    ap.add_argument("--orfs-var", action="append", help="KEY=VALUE passed to run_abi3_physical --orfs-var")
    ap.add_argument("--step-tcl", action="append", help="HOOK=path passed to run_abi3_physical --step-tcl")
    ap.add_argument("--balanced-clock", action="store_true",
                    help="W18b: CTS with macro clustering 1 (each hard macro clock pin its own driver; TritonCTS balances "
                         "the ETM insertion) -- the die-level balanced-clock method (tools/w18/clock_balance.py)")
    ap.add_argument("--slice-view", default="", help="pregionh: directory of the hardened pslice view")
    ap.add_argument("--pregion-h", type=float, default=0.0, help="pregion block height (um)")
    ap.add_argument("--tag", default="", help="suffix for the nickname and the output record directory")
    ap.add_argument("--abstract", action="store_true",
                    help="after a kept route: ORFS do-generate_abstract (write_abstract_lef + write_timing_model) "
                         "in <work>/<case>/orfs; prints the LEF/Liberty paths and digests")
    ap.add_argument("--phy-e8p5", action="store_true",
                    help="W18: fit the legal v2 PHY abstract ot_hbm3e_phy_v41x_aw30_e8p5 (265.584 um pseudo-channel "
                         "window, K pins 0.96-120.384 um), K port at 125.28-262.08 um, 60/25 ps SDC")
    ap.add_argument("--signoff-1p2", action="store_true",
                    help="W18 / AGENTS.md 2026-09-30: 1.2 GHz (0.833 ns), hardened at CORNER=WC, hold at WC and BC")
    a = ap.parse_args()
    if a.signoff_1p2:
        global CLOCK_NS, SIGNOFF_ARGS
        CLOCK_NS = 0.833
        SIGNOFF_ARGS = ["--orfs-corner", "WC", "--hold-corners", "WC,BC", "--orfs-var", "ADDER_MAP_FILE="]
    if a.phy_e8p5:
        global PHY_PC_WINDOW_UM, PC_PIN_SPAN, K_SPAN, HOLD_NS
        PHY_PC_WINDOW_UM, PC_PIN_SPAN, K_SPAN, HOLD_NS = 265.584, (0.96, 120.384), (125.28, 262.08), 0.025
        global EPC_OUTER
        EPC_OUTER = 2 * 4 + 2          # 8.5 mm PHY: the outermost region centre is 3.72 mm out -> 4 hops of <= 1 mm
        if a.signoff_1p2:
            EPC_OUTER = 2 * 8 + 2      # W15 SS reach 504 um: region centres 0.53-3.72 mm -> 2..8 hops
            global PROOT_HOPS
            PROOT_HOPS = (8, 6, 4, 2, 2, 4, 6, 8)
            global PROOT_H
            PROOT_H = 128.0            # 64 um: GRT-0183 (boxed in) with the deeper 0.5 mm-hop credit queues
    if a.slice_view:
        global SLICE_VIEW
        SLICE_VIEW = a.slice_view
    if a.pregion_h:
        global PREGION_H
        PREGION_H = a.pregion_h
    c = CASES[a.case]()
    if a.phy_e8p5:
        sfx = "_w18e8p5" + ("_1p2" if a.signoff_1p2 else "")
        c["nickname"] += sfx
        c["output"] = c["output"].replace("/physical.json", f"{sfx}/physical.json")
        c.setdefault("floorplan", {})["phy_view"] = "ot_hbm3e_phy_v41x_aw30_e8p5"
    args = list(c["args"])
    if a.density:
        args[args.index("--place-density") + 1] = f"{a.density:g}"
    for v in a.orfs_var or []:
        args += ["--orfs-var", v]
    if a.balanced_clock:
        args += ["--orfs-var", "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -macro_clustering_size 1 "
                               "-macro_clustering_max_diameter 20"]
    for v in a.step_tcl or []:
        args += ["--step-tcl", v]
    if a.tag:
        c["nickname"] += a.tag
        c["output"] = c["output"].replace("/physical.json", f"{a.tag}/physical.json")
    if a.stages:
        args[args.index("--stages") + 1] = a.stages
    argv = [sys.executable, str(ROOT / "tools/run_abi3_physical.py"), *args, "--nickname-tag", c["nickname"],
            "--output", a.output or c["output"], "--keep-workdir", str(a.work / a.case), "--force"]
    if a.print:
        print(json.dumps(c.get("floorplan"), indent=1))
    if a.print or not a.run:
        print(" ".join(x if len(x) < 200 else x[:80] + f"...<{len(x)} chars>" for x in argv))
    if a.run:
        (a.work / a.case).mkdir(parents=True, exist_ok=True)
        rc = subprocess.run(argv, cwd=ROOT).returncode
        if rc or not a.abstract:
            return rc
    if a.abstract:
        return abstract(a.work / a.case / "orfs")
    return 0


def abstract(orfs_dir: Path) -> int:
    import hashlib
    import re
    nick = re.search(r"DESIGN_NICKNAME\s*=\s*(\S+)", (orfs_dir / "config.mk").read_text()).group(1)
    top = re.search(r"DESIGN_NAME\s*=\s*(\S+)", (orfs_dir / "config.mk").read_text()).group(1)
    cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/src:ro", "-v", f"{orfs_dir}:/work", "-w",
           "/OpenROAD-flow-scripts/flow", "openroad/orfs:latest", "bash", "-lc",
           "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
           "make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base do-generate_abstract"]
    with (orfs_dir / "abstract.log").open("w") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    res = orfs_dir / "results/asap7" / nick / "base"
    out = {}
    for f in (res / f"{top}.lef", res / f"{top}_typ.lib"):
        out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    print(json.dumps({"returncode": rc, "abstracts": out}, indent=1))
    return rc if all(out.values()) else (rc or 1)


if __name__ == "__main__":
    sys.exit(main())
