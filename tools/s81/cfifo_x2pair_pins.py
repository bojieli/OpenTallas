#!/usr/bin/env python3
"""Pin plan of the static x2-pair column entry dsfd_cfifo (S-ELEM-PQ/COLL 2026-10-16, VIS-ROM S81F-02).

Die frame reference = the c21h elements.lef dsfd_cfifo view (431.976 x 95.016, origin O).  New outline 280.8 x 51.84 with
origin O + (103.68, 95.016 - 51.84): every N-face data pin keeps its ABSOLUTE die x and y (the cfifo still stands
8.95 um under the slot-0 station), only the depth shrinks (content ~7k um2; the old 41k um2 slot was ~83% empty).
  N  xa / xb       unchanged (pitch 0.048, aligned to sstn *_x2 xai / xbi, die verdict OK, jog 0)
     x2 [536]      pitch 0.096 from old x 136.416 = EXACTLY the station x2i column (station origin = cfifo + 36.72):
                   die jog 25.68 um -> 0 (the S81F-02 FAIL: 268 jog wires in the 9 um channel)
     cc / st       moved under the station cci (pitch 0.144) / so pins: jog 53 um -> 0
     ri / rs       after st (pitch 0.096)
     cr (core CTS root, x at the core-sink centroid, odd M5 track inside x2); the glue's ck->co / cr->rf clock
                   feed-throughs are gone (die drives the column clock root and the return-lane clock itself)
  S  xd [566]      pitch0.096 after g69 overflow diagnosis; all128 source-peer joins OPEN
     xf            beside xd (was 94 um west of its data)
     xd2 [538]     after xd with +27.216um coherent shift, pitch0.096; xf2 follows (odd track)
     rd [70]       same absolute start x, pitch 0.048 -> 0.096 (20.8 -> 10.4 b/um)
  W  rst at mid height
"""
import json, sys
from pathlib import Path

W = 280.8
# H: 51.84 (first kit, 189db3951/c3be51165) -> 69.12 (S-ELEM-PQ/CFIFO 2026-10-16): the 51.84 view measured post-CTS std
# 9,940 um2 = 76% of the core (max bin 1.145, ~30k hold buffers) and cr boundary spread 80.9 ps FAIL, the late sinks being
# the dense west xa/xb pin-flop strip (238-253 ps vs 172 ps).  The outline grows DOWNWARD only (N-face pins keep their
# absolute die x/y; S face moves 17.28 um south, still inside the legacy 95.016 slot): core 276.48 x 64.80 = 17,916 um2,
# ~0.56 of the measured post-CTS area.  Override with argv[2].
H = float(sys.argv[2]) if len(sys.argv) > 2 else 69.12
DX = 103.68                      # new frame x = old LEF x - DX
OFF = 0.012                      # M5/M4 track centre offset from the LEF rect edge
YN, YS = round(H - 0.042, 3), 0.042
rows = []


def put(name, layer, x, y):
    rows.append((name, layer, round(x, 3), round(y, 3)))


def bus(base, n, x0_old, pitch, face):
    for i in range(n):
        put(f"{base}[{i}]", "M5", x0_old + OFF - DX + pitch * i, YN if face == "N" else YS)
    return x0_old + OFF - DX + pitch * (n - 1)


bus("xa", 283, 108.144, 0.048, "N")
bus("xb", 266, 122.688, 0.048, "N")
x2_0 = 136.416 + OFF - DX
bus("x2", 536, 136.416, 0.096, "N")
bus("cc", 15, 188.832, 0.144, "N")
bus("st", 2, 191.952, 0.144, "N")
end = bus("ri", 66, 193.200, 0.096, "N")
# cr = core CTS root on the odd M5 track inside ri at x 94.38: the measured cr sink centroid of the 51.84 4_CTS ODB
# (2,324 sinks, centroid x 94.4 / y 37.0; was x 56.8 inside x2)
put("cr", "M5", 193.200 + OFF - DX + 0.096 * 50 + 0.048, YN)
put("rs", "M5", end + 0.192, YN)
xd_end = bus("xd", 566, 202.272, 0.096, "S")
put("xf", "M5", 202.272 + OFF - DX - 0.096, YS)
XD2_SHIFT = 27.216  # diagnostic leaf grant: separate the doubled-pitch xd receiver/hold band
xd2_0 = 230.400 + XD2_SHIFT + OFF - DX
bus("xd2", 538, 230.400 + XD2_SHIFT, 0.096, "S")
put("xf2", "M5", xd2_0 + 0.096 * 268 + 0.048, YS)
rd_0 = 372.096 + OFF - DX
bus("rd", 70, 372.096, 0.096, "S")
put("rst", "M4", 0.042, round(H / 2 + 0.012, 3))

xs = {}
for n, l, x, y in rows:
    assert 0 < x < W and 0 < y < H, (n, x, y)
    k = (l, x, y)
    assert k not in xs, f"pin overlap {n} {xs.get(k)}"
    xs[k] = n
out = Path(sys.argv[1] if len(sys.argv) > 1 else "physical/s81_die_pins/cfifo_x2pair")
out.mkdir(parents=True, exist_ok=True)
scal = {"cr", "rs", "xf", "xf2", "rst"}
with open(out / "dsfd_cfifo.tcl", "w") as f:
    f.write("# dsfd_cfifo static x2 pair: pin plan tools/s81/cfifo_x2pair_pins.py (S-ELEM-PQ/COLL 2026-10-16); 1-bit ports"
            " are scalars after synthesis\n")
    for n, l, x, y in rows:
        pn = n                                     # 1-bit [0:0] ports are scalars after synthesis
        f.write(f"place_pin -pin_name {{{pn}}} -layer {l} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary\n")
req = {"master": "dsfd_cfifo", "rtl": "rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_x2pair.sv",
       "grown": "S-ELEM-PQ/CFIFO 2026-10-16: 51.84 -> %.2f um high (down only) for core util ~0.56 of the measured post-CTS area; cr at the measured sink centroid x" % H,
       "old_view": {"outline": [431.976, 95.016], "source": "c21h a_real/elements.lef"},
       "new_outline": [W, H], "origin_shift_um": [DX, round(95.016 - H, 3)],
       "note": "absolute die x/y of xa/xb/x2-start/xd-start/rd-start kept; xd pitch doubled; xd2/xf2 shifted27.216um; x2 pitch = station x2i pitch (jog 0); cc/st under station cci/so; "
               "xd2/xf2 new pins (die bits had none); xf beside xd; rd pitch 0.096; ports ck/co/rf removed (clock feed-throughs: die drives ck_col_<r> and the rd return-lane clock from its column clock root)",
       "pins": len(rows), "south_pin_change": {"xd_pitch_um": 0.096, "xd2_xf2_shift_um": XD2_SHIFT, "north_unchanged": True, "grant": "S-DIE 2026-10-16 diagnostic leaf scope only; all128 source peer/reach/cut joins OPEN"}}
(out / "pin_request.json").write_text(json.dumps(req, indent=1) + "\n")
print(f"{len(rows)} pins -> {out}/dsfd_cfifo.tcl")
