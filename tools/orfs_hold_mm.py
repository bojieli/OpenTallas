#!/usr/bin/env python3
"""FLOW-HOLD (2026-10-07): patch a DISPOSABLE ORFS flow container's load.tcl / util.tcl so that, when the ORFS config
exports OT_HOLD_MM=1, every stage loads a multi-mode session (scene WC = SS setup, scene BC = FF hold, each under its own
constraints) and repair_timing_helper repairs SS setup and FF hold together (tools/orfs_hold_mm.tcl).  Without
OT_HOLD_MM=1 the patched scripts behave exactly as the originals.  Applied like tools/orfs_allcorner_spef.py: inside a new
--rm container only; images, work dirs and evidence are never modified.
   orfs_hold_mm.py <ORFS scripts dir> [<helper tcl, default /src/tools/orfs_hold_mm.tcl>]"""
import hashlib
import json
import sys
from pathlib import Path

LIB = "  source $::env(SCRIPTS_DIR)/read_liberty.tcl"
SDC = "  log_cmd read_sdc $::env(RESULTS_DIR)/$sdc_file"
RTH = "  log_cmd repair_timing {*}$additional_args\n}"


def patch(scripts: Path, helper: str) -> dict:
    load, util = scripts / "load.tcl", scripts / "util.tcl"
    lt, ut = load.read_text(), util.read_text()
    out = {"helper": helper}
    if "ot_mm_on" in lt and "ot_mm_sync" in ut:
        return {**out, "status": "already patched"}
    for name, text, anchor in (("load.tcl", lt, LIB), ("load.tcl", lt, SDC), ("util.tcl", ut, RTH)):
        if text.count(anchor) != 1:
            raise SystemExit(f"orfs_hold_mm: anchor {anchor!r} not found exactly once in {name}; refusing")
    lt = lt.replace(LIB, f"  source {helper}\n  if {{[ot_mm_on]}} {{ ot_mm_read_libs }} else {{\n{LIB}\n  }}", 1)
    lt = lt.replace(SDC, f"  if {{[ot_mm_on]}} {{ ot_mm_read_sdc $::env(RESULTS_DIR)/$sdc_file }} else {{\n{SDC}\n  }}", 1)
    # repair_timing_helper is the CTS / post-GRT (and placement) repair: refresh the FF mode before, restore after
    ut = ut.replace(RTH, "  if {[llength [info commands ot_mm_sync]]} { ot_mm_sync }\n"
                         "  set ot_rc [catch {log_cmd repair_timing {*}$additional_args} ot_msg ot_opts]\n"
                         "  if {[llength [info commands ot_mm_unsync]]} { ot_mm_unsync }\n"
                         "  if {$ot_rc} { return -options $ot_opts $ot_msg }\n}", 1)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
    out.update(load_before=sha(load.read_text()), util_before=sha(util.read_text()))
    load.write_text(lt)
    util.write_text(ut)
    out.update(status="patched", load_after=sha(lt), util_after=sha(ut))
    return out


if __name__ == "__main__":
    print("orfs_hold_mm:", json.dumps(patch(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "/src/tools/orfs_hold_mm.tcl")))
