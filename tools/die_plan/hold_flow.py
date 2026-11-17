"""Install the sign-off IO frame and the final coupled repair on fresh kits.

Existing run directories are never changed by generation.  Single-FF GRT repair
uses the same reference decision as signoff.py; hard-core bound contracts keep
their declared reference.  The final repair itself runs only in an existing
TT/FF coupled session and does not create or change timing modes.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil

import vclk_ref

HERE = Path(__file__).resolve().parent
FINAL = "source /work/core_final_repair.tcl\n"


def install(kit, *, measured=None):
    kd = Path(kit)
    cfg = kd / "config.mk"
    text = cfg.read_text()
    if measured is None:
        measured = os.environ.get("OT_GRT_MEASURED_HOLD", "1") != "0"
    ref = vclk_ref.ff_reference(kd)
    use = measured and ref["ref"] == "rebind"
    # Owned helpers are staged together; no hook points outside the frozen kit.
    for name in ("core_final_repair.tcl",):
        shutil.copyfile(HERE / name, kd / name)
    if use:
        for name in ("vclk_measured_hold.tcl", "vclk_ref.py"):
            shutil.copyfile(HERE / name, kd / name)
    text = re.sub(r"(?m)^\s*(?:override\s+)?export\s+OT_GRT_MEASURED_HOLD\s*=.*\n?", "", text)
    if use:
        text += "export OT_GRT_MEASURED_HOLD = 1\n"
    # Secondary-clock/native source installers can append SDC after the first
    # config is emitted. Hash the final golden file, not that earlier version.
    text = re.sub(r"(?m)^\s*(?:override\s+)?export\s+OT_SIGNOFF_SDC_SHA\s*=.*\n?", "", text)
    text += "export OT_SIGNOFF_SDC_SHA = " + hashlib.sha256((kd / "constraint.sdc").read_bytes()).hexdigest()[:16] + "\n"
    cfg.write_text(text)
    post = kd / "grt_post.tcl"
    body = post.read_text()
    cleanup = []
    keep = []
    for line in body.splitlines():
        if line.strip() == FINAL.strip():
            continue
        if line.strip() in (
            'if {[llength [info procs ot_pgtt_remove]]} { ot_pgtt_remove }',
            'if {[llength [info procs ot_pgcko_remove]]} { ot_pgcko_remove }',
        ):
            cleanup.append(line)
        else:
            keep.append(line)
    # All post-GRT data repair still sees the actual PG routing/placement
    # model. Temporary constraints are removed only before checkpoint output.
    post.write_text("\n".join(keep).rstrip() + "\n" + FINAL +
                    ("\n".join(cleanup) + "\n" if cleanup else ""))
    return dict(measured_hold=bool(use), reference=ref["ref"])
