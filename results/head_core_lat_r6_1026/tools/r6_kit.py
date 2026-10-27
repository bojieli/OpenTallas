#!/usr/bin/env python3
"""HEAD-CORE-LAT-R6 elemB kit: from the R5 N-band probe kit (elemB_n50) build elemB_r6:
 - wrapper RTL = R6 ot_s81hd_elemB_rb.sv (l_v/l_d/done/best_* removed, u_bin_jn deleted)
 - io.tcl / pins.json: removed output ports dropped; the 26 N-face pins (o_v, o_d[24], fault) re-pinned top-down to
   the S face (the face toward the A elements u_eA2/u_eA3 below u_eB in hd_tile; with the ROMs in the N band the S face
   borders std-cell rows, so the pin registers land in the logic area, none above the ROM band), on the M5 track
   grid of the existing S-face pins (x = 0.78 + 0.096 k), pitch 2 tracks, inside the x range freed by the removed pins
 - face_guard skip: clk|rst_n + declared dead inputs row0|b_v|b_d (dead_inputs.json proves no load)
usage: r6_kit.py SRC_KIT DST_KIT NEW_WRAPPER
"""
import json, re, shutil, sys
from pathlib import Path
src, dst, wrapper = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
assert not dst.exists()
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("run", "__pycache__", "*.geo", "trial.log", "image.txt",
                                                       "face_guard.json", "sdc_lint.log", "orfs_hold_mm.log",
                                                       "netlist_1_2_yosys.v"))
shutil.copy(wrapper, dst / "rtl/ot_s81hd_elemB_rb.sv")
REMOVED = ("l_v", "l_d", "done", "best_row", "best_bits", "best_key")
DEAD = ("row0", "b_v", "b_d")
pins = json.loads((dst / "pins.json").read_text())
north = sorted([p for p in pins if p["face"] == "N"], key=lambda p: p["x"])
assert len(north) == 26 and {p["bus"] for p in north} == {"o_v", "o_d", "fault"}, north
keep = [p for p in pins if p["bus"] not in REMOVED]
s_used = {round(p["x"], 3) for p in keep if p["face"] == "S"}
# slots: M5 track grid of the S face, every 2nd track, starting in the freed band at x >= 196.044
slots, k = [], int(round((196.044 - 0.78) / 0.096))
while len(slots) < 26:
    x = round(0.78 + 0.096 * k, 3)
    if all(abs(x - u) > 0.15 for u in s_used):
        slots.append(x)
    k += 2
moved = {}
for p, x in zip(north, slots):
    moved[(p["bus"], p["bit"])] = x
    p.update(face="S", x=x, y=0.042)
(dst / "pins.json").write_text(json.dumps(keep, indent=1) + "\n")
out = []
nm = lambda b, i: b if b in ("o_v", "fault") else f"{b}[{i}]"
movedn = {nm(b, i): x for (b, i), x in moved.items()}
for l in (dst / "io.tcl").read_text().splitlines():
    m = re.search(r"-pin_name \{(\S+?)\}", l)
    if m:
        bus = re.sub(r"\[.*", "", m[1])
        if bus in REMOVED:
            continue
        if m[1] in movedn:
            l = re.sub(r"-location \{\S+ \S+\} -pin_size \{\S+ \S+\}",
                       "-location {%.4f 0.0420} -pin_size {0.0240 0.0840}" % movedn[m[1]], l)
    out.append(l)
out.insert(1, "# HEAD-CORE-LAT-R6 10-26: l_v/l_d/done/best_* removed (unused); 26 N-face pins (o_v/o_d/fault) re-pinned "
              "top-down to the S face (toward the A elements; no pin register above the N-band ROMs)")
(dst / "io.tcl").write_text("\n".join(out) + "\n")
(dst / "face_guard_skip.txt").write_text("^(clk|rst_n|row0|b_v|b_d)$\n")
# geometry dump name used by head_elemB_place.sh stays elemB_r5_3place.geo; record the kit delta
(dst / "R6_KIT.json").write_text(json.dumps(dict(
    src=str(src), removed_ports=REMOVED, dead_inputs=DEAD, moved_to_S={k: v for k, v in movedn.items()},
    pins=len(keep), north_left=sum(p["face"] == "N" for p in keep)), indent=1) + "\n")
print("R6 kit", dst, "pins", len(keep), "moved", len(movedn), "x", slots[0], slots[-1])
