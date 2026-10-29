"""Restore source-declared RING capture vectors through OpenROAD synth cleanup.
Apply to a fresh generated RING kit; then run its ordinary SYNTH/LEC/physical gates.
No RTL, pins, clock constraints or cycle contract changes.
"""
import json
from pathlib import Path
import shutil
import sys

kit = Path(sys.argv[1]).resolve()
f = json.loads((kit / "freeze.json").read_text())
if f.get("module") != "ot_hfd_coll_q2_hard_v8g__ring_ag":
    raise SystemExit("RING-only helper: unexpected module")
here = Path(__file__).resolve().parent
for name in ("capture_keep.tcl", "capture_release.tcl"):
    shutil.copyfile(here / name, kit / name)
pre = kit / "face_keep.tcl"
s = pre.read_text()
if "source /work/capture_keep.tcl" not in s:
    pre.write_text(s + "\nsource /work/capture_keep.tcl\n")
post = kit / "post_synth_actual.tcl"
s = post.read_text()
if "source /work/capture_release.tcl" not in s:
    if "write_verilog" not in s:
        raise SystemExit("expected canonical post-eliminate netlist hook missing")
    post.write_text(s.replace("write_verilog", "source /work/capture_release.tcl\nwrite_verilog", 1))
# A cached pre-place ODB may predate the release hook. Release just these capture
# cells again before data resizing; face-register placement protection is separate.
place = kit / "face_flops.tcl"
s = place.read_text()
if "source /work/capture_release.tcl" not in s:
    place.write_text("source /work/capture_release.tcl\n" + s)
print("RING_CAPTURE_KEEP_INSTALLED", kit)
