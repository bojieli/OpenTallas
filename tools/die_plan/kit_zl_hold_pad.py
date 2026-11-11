#!/usr/bin/env python3
"""HEAD-92 11-10 form ZLP: put zero-logic hold pads into a generated kit (stage resume from CTS).

zl_hold_pad.tcl (PRE_CTS) keeps ONE HB4xp67 in front of every register / SRAM input whose driver reaches a register
Q/QN through at most OT_ZLP_DEPTH BUF/INV cells.  Such hops have clk-Q + one INV (~43 ps FF) of data delay, below
25 ps hold uncertainty + ~14 ps hold time + leaf / tap skew, so they are the FF hold class that GRT hold repair chases
for hours (hd_mesh a2 0432aced49ac: 8,700 -> 526 endpoints in 3 h, 1,754 after route).

  kit_zl_hold_pad.py KIT [--depth 4] [--slew-margin 20] [--cap-margin 20] [--report-only]

Writes KIT/zl_hold_pad.tcl, sources it first in KIT/pre_cts.tcl (kept copy pre_cts.tcl.pre_zlp), appends the OT_ZLP
exports to KIT/config.mk and writes KIT/resume.json {"start": "cts"} unless one exists.  Idempotent.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TCL = HERE / "zl_hold_pad.tcl"
MARK = "# OT_ZLP kit_zl_hold_pad.py"
SRC = "source /work/zl_hold_pad.tcl"


def apply(kit: Path, depth=4, slew=20, cap=20, report_only=False):
    kit = Path(kit)
    pre = kit / "pre_cts.tcl"
    cfg = kit / "config.mk"
    if not pre.is_file() or not cfg.is_file():
        raise SystemExit(f"kit_zl_hold_pad: {kit} has no pre_cts.tcl / config.mk")
    shutil.copyfile(TCL, kit / "zl_hold_pad.tcl")
    text = pre.read_text()
    if SRC not in text:
        shutil.copyfile(pre, kit / "pre_cts.tcl.pre_zlp")
        pre.write_text(f"{MARK}: zero-logic hold pads before the tap trees\n{SRC}\n{text}")
    c = cfg.read_text()
    if MARK not in c:
        lines = [MARK, "export OT_ZLP = 1", f"export OT_ZLP_DEPTH = {int(depth)}"]
        if report_only:
            lines.append("export OT_ZLP_REPORT_ONLY = 1")
        if slew is not None:
            lines.append(f"export SLEW_MARGIN = {int(slew)}")
        if cap is not None:
            lines.append(f"export CAP_MARGIN = {int(cap)}")
        cfg.write_text(c.rstrip("\n") + "\n" + "\n".join(lines) + "\n")
    rs = kit / "resume.json"
    if not rs.exists():
        rs.write_text(json.dumps({"start": "cts"}) + "\n")
    return {"kit": str(kit), "pre_cts": SRC in pre.read_text(), "resume": json.loads(rs.read_text())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--slew-margin", type=int, default=20)
    ap.add_argument("--cap-margin", type=int, default=20)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(apply(Path(a.kit), a.depth, a.slew_margin, a.cap_margin, a.report_only)))


if __name__ == "__main__":
    sys.exit(main())
