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
BUFFER_HOOK = "physical/abi3/v41x_karb_repair_buffer_cap.tcl"
KARB = ["rtl/chip/ot_chip_v41x_karb_q2.sv", "rtl/chip/ot_chip_v41x_karb_qn.sv"]


def common(top: str, sources: list[str], w: float, h: float, params: list[str] = (), density: float = 0.6):
    m = 4 * ROW_UM
    args = ["--view", "asap7", "--top", top]
    for s in sources:
        args += ["--source", s]
    for p in params:
        args += ["--param", p]
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
        r"k_wstrb|k_rsp_tag|k_rsp_beat|k_rsp_data)\[\d+\]$" + f"=top:{200:g}-{370:g}",
    ]
    args = common("ot_chip_v41x_karb_slice", ["rtl/chip/ot_chip_v41x_karb_slice.sv"], w, h, [f"AW={AW}"])
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": f"w2a_karb_slice_aw30{tag}",
            "output": f"results/physical_abi3/asap7/chip/v41x_karb_local/slice_aw30{tag}/physical.json",
            "floorplan": {"die_um": [w, h], "pc_pin_span_um": PC_PIN_SPAN, "k_span_um": [200, 370]}}


def region_case(h: float = ENV_H, tag: str = "") -> dict:
    w = 4 * PHY_PC_WINDOW_UM
    regions = []
    for p in range(4):
        x0 = p * PHY_PC_WINDOW_UM
        regions.append(f"{pin_regex(karb_pc_pins(p, 'h', aw=AW))}=bottom:{span(x0, *PC_PIN_SPAN)}")
        regions.append(f"{pin_regex(karb_pc_pins(p, 'b', aw=AW))}=top:{span(x0, *PC_PIN_SPAN)}")
    regions.append(r"^(kq_v|kq_rdy|kq_we|clk|rst_n)$|^(kq_lpc|kq_addr|kq_len|kq_tag|kq_wdata|kq_wstrb)\[\d+\]$"
                   + f"=top:{span(PHY_PC_WINDOW_UM, 200, 370)}")
    regions.append(r"^(ks_v|ks_cr|k_wr_done)$|^(ks_tag|ks_beat|ks_data|b_grant_n|contend_n)\[\d+\]$"
                   + f"=top:{span(2 * PHY_PC_WINDOW_UM, 200, 370)}")
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


BAND_H = 17.28   # the current floorplan's KV/key/staging band height (12,000 x 17.2 um), on the row grid
CASES = {"slice": slice_case, "region": region_case, "stack_ep": stack_ep_case, "trunk_far": trunk_case,
         # the existing band budget instead of the proposal's 64 um study envelope
         "slice_band": lambda: slice_case(BAND_H, "_band"), "region_band": lambda: region_case(BAND_H, "_band"),
         # endpoint at the stack end (outermost region at 11.25 mm) and a mid-distance region (2.25 mm)
         "trunk_end": lambda: trunk_case(11400.0, "_end"), "trunk_mid": lambda: trunk_case(3150.0, "_mid")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--work", type=Path, default=Path(os.environ.get("OT_V41PNR_WORK", "/home/ubuntu/w2/pnr")))
    ap.add_argument("--output")
    ap.add_argument("--stages")
    ap.add_argument("--density", type=float, help="override the global placement density")
    ap.add_argument("--abstract", action="store_true",
                    help="after a kept route: ORFS do-generate_abstract (write_abstract_lef + write_timing_model) "
                         "in <work>/<case>/orfs; prints the LEF/Liberty paths and digests")
    a = ap.parse_args()
    c = CASES[a.case]()
    args = list(c["args"])
    if a.density:
        args[args.index("--place-density") + 1] = f"{a.density:g}"
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
