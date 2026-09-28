#!/usr/bin/env python3
"""Place-and-route cases of the adopted V4.1 layer die at the design clock (1.087 GHz, 0.92 ns), ASAP7.

Each case is a floorplan derived from the die-assembly study (docs/ARCH_V41_DIE_ASSEMBLY.md,
results/arch/v41_die_assembly.json) and run through tools/run_abi3_physical.py, so every record has the
repository's physical.json schema, source pins and acceptance verdict.

  karb_strip   ot_chip_v41x_hbm_karb (one HBM3E stack's K-port arbiter, NPC = 32) as the strip the
               die-assembly floorplan draws beside each HBM3E PHY ("KV/key streamer + staging", along the
               PHY's 12.0 mm core-facing edge).  Pins follow the floorplan: pseudo-channel p's stack-side
               (h_*, r_*) bits on the bottom edge and its bridge-side (b_*) bits on the top edge, both inside
               p's 375 um window of the PHY edge (PHY_PC_WINDOW_UM); the KV prefetch's one K channel and
               the status counters at the spine end (x = 12 mm).  The standalone attempt
               (results/physical_abi3/asap7/chip/v41x_hbm_karb/physical.json) left the 40,332 pins to the
               default placer on a 122 um square and failed PPL-0024.

    python3 tools/v41x_die_pnr.py karb_strip --print          # the run_abi3_physical argv
    OT_ORFS_NUM_CORES=8 python3 tools/v41x_die_pnr.py karb_strip --run --work /home/ubuntu/v41dpnr/work
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOCK_NS = 0.92                    # 1.087 GHz (results/arch/v41_die_assembly.json clock_hz)
PHY_EDGE_UM = 12000.0              # HBM3E PHY core-facing edge (die assembly: 12.0 x 0.8335 mm per stack)
NPC = 32
PHY_PC_WINDOW_UM = PHY_EDGE_UM / NPC
PC_PIN_SPAN = (20.0, 195.0)        # pin sub-window inside each pseudo-channel window, um from its left end
ROW_UM = 0.27


def bits(name: str, width: int, lo: int = 0) -> list[str]:
    return [f"{name}[{i}]" for i in range(lo, lo + width)]


def pin_regex(pins: list[str]) -> str:
    """A Tcl regexp matching exactly these bus bits (grouped per bus)."""
    by_bus: dict[str, list[str]] = {}
    for p in pins:
        n, _, rest = p.partition("[")
        by_bus.setdefault(n, []).append(rest.rstrip("]"))
    alts = [f"^{n}\\[({'|'.join(ix)})\\]$" for n, ix in by_bus.items()]
    return "|".join(alts)


def karb_pc_pins(p: int, side: str, aw: int = 28, tagw: int = 16, lenw: int = 4, beatw: int = 4,
                 dw: int = 256) -> list[str]:
    """Pseudo-channel p's bits on one side of ot_chip_v41x_hbm_karb: 'b' the pooled bridge, 'h' the stack."""
    if side == "b":
        spec = [("b_v", 1), ("b_rdy", 1), ("b_addr", aw), ("b_len", lenw), ("b_tag", tagw), ("b_we", 1),
                ("b_wdata", dw), ("b_wstrb", dw // 8), ("b_wr_done", 1), ("b_rsp_v", 1), ("b_rsp_rdy", 1),
                ("b_rsp_tag", tagw), ("b_rsp_beat", beatw), ("b_rsp_data", dw)]
    else:
        spec = [("h_v", 1), ("h_rdy", 1), ("h_addr", aw), ("h_len", lenw), ("h_tag", tagw + 1), ("h_we", 1),
                ("h_wdata", dw), ("h_wstrb", dw // 8), ("h_wr_done", 1), ("r_v", 1), ("r_rdy", 1),
                ("r_tag", tagw + 1), ("r_beat", beatw), ("r_data", dw)]
    out = []
    for name, w in spec:
        out += bits(name, w, p * w)
    return out


def karb_strip(height_um: float = 30.24) -> dict:
    w, h = PHY_EDGE_UM, height_um
    m = 8 * ROW_UM
    regions = []
    for p in range(NPC):
        x0 = p * PHY_PC_WINDOW_UM
        span = f"{x0 + PC_PIN_SPAN[0]:g}-{x0 + PC_PIN_SPAN[1]:g}"
        regions.append(f"{pin_regex(karb_pc_pins(p, 'h'))}=bottom:{span}")
        regions.append(f"{pin_regex(karb_pc_pins(p, 'b'))}=top:{span}")
    k = r"^k_(v|rdy|we|wr_done|rsp_v|rsp_rdy)$|^k_(addr|len|tag|wdata|wstrb|rsp_tag|rsp_beat|rsp_data)\[\d+\]$"
    regions.append(f"{k}=top:{w - 165:g}-{w - 5:g}")
    regions.append(r"^(k_grants|b_grants|contended)\[\d+\]$" + f"=top:{w - 540:g}-{w - 370:g}")
    regions.append(f"^(clk|rst_n)$=top:{w / 2 - 20:g}-{w / 2 + 20:g}")
    args = ["--view", "asap7", "--top", "ot_chip_v41x_hbm_karb", "--source", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
            "--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2", "--stages", "synth,pnr",
            "--die-area", "0", "0", f"{w:g}", f"{h:g}",
            "--core-area", f"{m:g}", f"{m:g}", f"{w - m:g}", f"{h - m:g}",
            "--place-density", "0.60"]
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": "claude_v41x_karb_strip",
            "output": "results/asap7_physical/v41x_die_karb/physical.json",
            "floorplan": {"die_um": [w, h], "pc_window_um": PHY_PC_WINDOW_UM, "pc_pin_span_um": PC_PIN_SPAN}}


CASES = {"karb_strip": karb_strip}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--work", type=Path, default=Path(os.environ.get("OT_V41PNR_WORK", "/home/ubuntu/v41dpnr/work")))
    ap.add_argument("--output")
    a = ap.parse_args()
    c = CASES[a.case]()
    argv = [sys.executable, str(ROOT / "tools/run_abi3_physical.py"), *c["args"], "--nickname-tag", c["nickname"],
            "--output", a.output or c["output"], "--keep-workdir", str(a.work / a.case), "--force"]
    if a.print or not a.run:
        print(" ".join(x if len(x) < 200 else x[:80] + f"...<{len(x)} chars>" for x in argv))
        print(f"{len(argv)} arguments, {sum(len(x) for x in argv)} bytes")
    if a.run:
        (a.work / a.case).mkdir(parents=True, exist_ok=True)
        return subprocess.run(argv, cwd=ROOT).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
