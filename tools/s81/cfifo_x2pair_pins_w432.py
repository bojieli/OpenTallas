#!/usr/bin/env python3
"""Pin plan of dsfd_cfifo in the FULL legacy die slot 431.976 x 95.016 (S-ELEM-PQ/CFIFO Claude 2026-10-16, VIS-ROM S81F-02b).

Why: g69 (280.8 x 69.12, xd pitch 0.048) failed GRT with 677 overflow, all in y0..10 / x80..140 = the xd pin wall
(566 bits in 27.1 um, every M5 track) with its ot_inhold/ot_ihdrv hold stages piled on it; N pins spanned 91.5 of 280.8 um
(xa 283 in 13.5 um, xb 266 in 12.7 um).  Owner 10-16: closure first, area/height growth OK.
Frame = the legacy c21h elements.lef slot frame itself (DX 0, H 95.016): no origin shift, every unchanged pin keeps its
absolute die x/y.
  N  xb [266]   pitch 0.096, ends 1 track west of xa start (moved WEST of xa; was interleaved east of xa at 0.048)
     xa [283]   pitch 0.096 from the same absolute x 108.144
     x2 [536]   unchanged: pitch 0.096 from 136.416 = station x2i column (jog 0)
     cc/st/ri/cr/rs unchanged
  S  xd [566]   pitch XD (argv[2], default 0.144) from the same absolute x 202.272; xf one track west of xd
     xd2 [538]  pitch 0.096 right after xd (+1.104 um gap); xf2 at its middle (odd track)
     rd [70]    unchanged absolute start 372.096, pitch 0.096
  W  rst mid height
"""
import json, sys
from pathlib import Path

W, H = 431.976, 95.016
XD = float(sys.argv[2]) if len(sys.argv) > 2 else 0.144
OFF = 0.012
YN, YS = round(H - 0.042, 3), 0.042
rows = []


def put(name, layer, x, y):
    rows.append((name, layer, round(x, 3), round(y, 3)))


def bus(base, n, x0, pitch, face):
    for i in range(n):
        put(f"{base}[{i}]", "M5", x0 + OFF + pitch * i, YN if face == "N" else YS)
    return x0 + OFF + pitch * (n - 1)


bus("xa", 283, 108.144, 0.096, "N")
bus("xb", 266, 108.144 - 0.096 * 266, 0.096, "N")
bus("x2", 536, 136.416, 0.096, "N")
bus("cc", 15, 188.832, 0.144, "N")
bus("st", 2, 191.952, 0.144, "N")
end = bus("ri", 66, 193.200, 0.096, "N")
put("cr", "M5", 193.200 + OFF + 0.096 * 50 + 0.048, YN)
put("rs", "M5", end + 0.192, YN)
xd_end = bus("xd", 566, 202.272, XD, "S")
put("xf", "M5", 202.272 + OFF - 0.096, YS)
xd2_0 = round(xd_end - OFF + 1.104, 3)
bus("xd2", 538, xd2_0, 0.096, "S")
put("xf2", "M5", xd2_0 + OFF + 0.096 * 268 + 0.048, YS)
assert xd2_0 + 0.096 * 538 < 372.096, "xd2 runs into rd"
bus("rd", 70, 372.096, 0.096, "S")
put("rst", "M4", 0.042, round(H / 2 + 0.012, 3))

xs = {}
for n, l, x, y in rows:
    assert 0 < x < W and 0 < y < H, (n, x, y)
    k = (l, x, y)
    assert k not in xs, f"pin overlap {n} {xs.get(k)}"
    xs[k] = n
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
with open(out / "dsfd_cfifo.tcl", "w") as f:
    f.write("# dsfd_cfifo static x2 pair, full legacy slot 431.976x95.016: tools/s81/cfifo_x2pair_pins_w432.py xd pitch %.3f\n" % XD)
    for n, l, x, y in rows:
        f.write(f"place_pin -pin_name {{{n}}} -layer {l} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary\n")
req = {"master": "dsfd_cfifo", "rtl": "rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_x2pair.sv",
       "grown": "S-ELEM-PQ/CFIFO Claude 2026-10-16: back to the full legacy die slot 431.976x95.016 (closure first, VIS-ROM S81F-02b pin wall)",
       "old_view": {"outline": [431.976, 95.016], "source": "c21h a_real/elements.lef"},
       "new_outline": [W, H], "origin_shift_um": [0.0, 0.0],
       "note": "xa/xb pitch 0.048->0.096 (xb moved west of xa), xd pitch %.3f, xd2 follows xd at 0.096, x2/cc/st/ri/cr/rs/rd absolute unchanged; ck/co/rf removed" % XD,
       "pins": len(rows),
       "grant": "diagnostic leaf scope; all 128 source peer/reach/cut joins and the parent pin/clock REBIND are OPEN (S-DIE)"}
(out / "pin_request.json").write_text(json.dumps(req, indent=1) + "\n")
print(f"{len(rows)} pins -> {out}/dsfd_cfifo.tcl  xd {202.284:.3f}..{xd_end:.3f} xd2 {xd2_0:.3f}..{xd2_0 + 0.096 * 537:.3f}")
