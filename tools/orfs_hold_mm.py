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
# unstick 2026-10-08: the hold-stall guard (ot_repair_timing in orfs_hold_mm.tcl), when the helper defines it
GUARD_CALL = ("  if {[llength [info commands ot_repair_timing]]} {\n"
              "    set ot_rc [catch {ot_repair_timing $additional_args} ot_msg ot_opts]\n"
              "  } else {\n"
              "    set ot_rc [catch {log_cmd repair_timing {*}$additional_args} ot_msg ot_opts]\n"
              "  }\n")


def patch(scripts: Path, helper: str) -> dict:
    load, util = scripts / "load.tcl", scripts / "util.tcl"
    lt, ut = load.read_text(), util.read_text()
    out = {"helper": helper}
    if "ot_mm_on" in lt and "ot_repair_timing" in ut:
        return {**out, "status": "already patched"}
    old_catch = "  set ot_rc [catch {log_cmd repair_timing {*}$additional_args} ot_msg ot_opts]\n"
    if "ot_mm_on" in lt and "ot_mm_sync" in ut and ut.count(old_catch) == 1:   # earlier generation: add the hold guard
        util.write_text(ut.replace(old_catch, GUARD_CALL, 1))
        return {**out, "status": "upgraded (hold-stall guard)"}
    for name, text, anchor in (("load.tcl", lt, LIB), ("load.tcl", lt, SDC), ("util.tcl", ut, RTH)):
        if text.count(anchor) != 1:
            raise SystemExit(f"orfs_hold_mm: anchor {anchor!r} not found exactly once in {name}; refusing")
    lt = lt.replace(LIB, f"  source {helper}\n  if {{[ot_mm_on]}} {{ ot_mm_read_libs }} else {{\n{LIB}\n  }}", 1)
    lt = lt.replace(SDC, f"  if {{[ot_mm_on]}} {{ ot_mm_read_sdc $::env(RESULTS_DIR)/$sdc_file }} else {{\n{SDC}\n  }}", 1)
    # repair_timing_helper is the CTS / post-GRT (and placement) repair: refresh the FF mode before, restore after
    ut = ut.replace(RTH, "  if {[llength [info commands ot_mm_sync]]} { ot_mm_sync }\n"
                         "  if {[llength [info commands ot_repair_timing]]} {\n"
                         "    set ot_rc [catch {ot_repair_timing $additional_args} ot_msg ot_opts]\n"
                         "  } else {\n"
                         "    set ot_rc [catch {log_cmd repair_timing {*}$additional_args} ot_msg ot_opts]\n"
                         "  }\n"
                         "  if {[llength [info commands ot_mm_unsync]]} { ot_mm_unsync }\n"
                         # flow-triage 2026-10-08: an mm repair that exhausts repair_timing's buffer budget (RSZ-0060)
                         # throws AFTER inserting its buffers, killing the stage (no 4_1_cts.odb) although the design is
                         # whole; continue in mm mode only (tolerate_flow_errors then zeroes the count) so the sign-off
                         # STA, not a dead stage, reports the residual FF hold.
                         "  if {$ot_rc && [info exists ::ot_mm_active] && [regexp {RSZ-0060|Max buffer count} $ot_msg]} {\n"
                         "    puts \"OT_HOLD_MM: repair hit the buffer cap (RSZ-0060); continuing on the repaired design, sign-off decides\"\n"
                         "    return\n  }\n"
                         "  if {$ot_rc} { return -options $ot_opts $ot_msg }\n}", 1)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
    out.update(load_before=sha(load.read_text()), util_before=sha(util.read_text()))
    load.write_text(lt)
    util.write_text(ut)
    out.update(status="patched", load_after=sha(lt), util_after=sha(ut))
    return out


STAGE_LOGS = {"cts": ["4_1_cts.log"], "globalroute": ["5_1_grt.log"]}


def tolerate_flow_errors(errors: dict, logs_dir) -> dict:
    """An mm repair that runs out of buffer budget (RSZ-0060) inside a recipe's own multi-pass wrapper
    (qwen_die_masters/repair_budget.tcl continues on the grown design) logs one [ERROR] although the stage then
    completes: such a count is zeroed ONLY when every [ERROR line of the stage log is RSZ-0060, their number equals the
    count, and an "OT_HOLD_MM after repair" line follows the last one.  Anything else stays an error."""
    out = dict(errors)
    for key, val in errors.items():
        stage = key.split("__", 1)[0]
        if not int(val) or stage not in STAGE_LOGS:
            continue
        lines = []
        for name in STAGE_LOGS[stage]:
            f = Path(logs_dir) / name
            if f.is_file():
                lines += f.read_text(errors="replace").splitlines()
        errs = [i for i, ln in enumerate(lines) if ln.startswith("[ERROR")]
        if (errs and len(errs) == int(val) and all("RSZ-0060" in lines[i] for i in errs)
                and any("OT_HOLD_MM after repair" in ln for ln in lines[errs[-1]:])):
            out[key] = 0
            print(f"orfs_hold_mm: {key}={val} tolerated (RSZ-0060 inside a completed multi-pass mm repair)")
    return out


if __name__ == "__main__":
    print("orfs_hold_mm:", json.dumps(patch(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "/src/tools/orfs_hold_mm.tcl")))
