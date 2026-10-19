#!/usr/bin/env python3
"""Top-down N-face pin plan for qfd_d2d_static (HF-2, HARD-REVIEW 10-18 row 2).

Reads the closed view's LEF (r8c, the pins the compute die binds today) and writes an exact place_pin io_tcl:
  * S / W / E pins: literal copy of the closed view (unchanged geometry);
  * N pins: the same bus order (sorted by the closed x) spread evenly over x LO..HI (<= 6 pins/um) on M5 tracks
    (x = 0.012 + k * 0.048, >= 2 tracks apart), so no pin-flop group sits in the NW corner behind g_bank[2];
  * ck: moved from the E face to the N face at the SRAM column-channel centre (between g_bank[2] and g_bank[3]).
0 cycles, 0 area: outline, macros and RTL are untouched.
Usage: qfd_d2d_n_face_pins.py VIEW.lef OUT.tcl [--lo 120] [--hi 400] [--ck-x 237.492] [--json OUT.json]
"""
import argparse, json, re

W, H = 475.2, 280.8
M5_OFF, M5_PITCH = 0.012, 0.048


def lef_pins(path):
    t = open(path).read()
    out = []
    for m in re.finditer(r"\n  PIN (\S+)\n(.*?)\n  END \1", t, re.S):
        n, b = m.group(1), m.group(2)
        if "USE POWER" in b or "USE GROUND" in b:
            continue
        lay = re.search(r"LAYER (\S+) ;", b).group(1)
        r = [float(x) for x in re.search(r"RECT\s+(\S+) (\S+) (\S+) (\S+)", b).groups()]
        out.append((n, lay, r))
    return out


def face(r):
    x0, y0, x1, y1 = r
    if y0 < 0.2: return "S"
    if y1 > H - 0.2: return "N"
    if x0 < 0.2: return "W"
    if x1 > W - 0.2: return "E"
    raise SystemExit(f"pin rect {r} not on a face")


def snap(x):
    return round(M5_OFF + round((x - M5_OFF) / M5_PITCH) * M5_PITCH, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lef"); ap.add_argument("out")
    ap.add_argument("--lo", type=float, default=120.0); ap.add_argument("--hi", type=float, default=400.0)
    ap.add_argument("--ck-x", type=float, default=(45.792 + 171.288 + 257.904) / 2)   # column-channel centre
    ap.add_argument("--json")
    a = ap.parse_args()
    pins = lef_pins(a.lef)
    keep, north = [], []
    for n, lay, r in pins:
        f = face(r)
        if n == "ck":
            continue
        (north if f == "N" else keep).append((n, lay, r, f))
    north.sort(key=lambda p: (p[2][0] + p[2][2]) / 2)
    nslot = len(north) + 1
    step = (a.hi - a.lo) / (nslot - 1)
    xs = [a.lo + i * step for i in range(nslot)]
    ck_i = min(range(nslot), key=lambda i: abs(xs[i] - a.ck_x))
    xs[ck_i] = a.ck_x
    xs = [snap(x) for x in xs]
    gaps = [b - a_ for a_, b in zip(xs, xs[1:])]
    assert min(gaps) >= 2 * M5_PITCH - 1e-6, min(gaps)
    lines = ["# HF-2 10-18 (tools/qwen_split/qfd_d2d_n_face_pins.py): top-down N-face plan for qfd_d2d_static.",
             f"# S/W/E = closed r8c view literal; N bus order kept, spread over x {a.lo:g}-{a.hi:g} ({len(north)} pins, "
             f"{len(north)/(a.hi-a.lo):.2f}/um); ck moved E -> N at x {xs[ck_i]:.3f} (SRAM column channel)."]
    rows = []
    def emit(n, lay, cx, cy, w, h):
        lines.append(f"place_pin -pin_name {{{n}}} -layer {lay} -location {{{cx:.6f} {cy:.6f}}} -pin_size {{{w:.6f} {h:.6f}}}")
        rows.append({"pin": n, "layer": lay, "x": round(cx, 4), "y": round(cy, 4)})
    for n, lay, r, f in sorted(keep, key=lambda p: p[0]):
        emit(n, lay, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r[2] - r[0], r[3] - r[1])
    it = iter(north)
    for i, x in enumerate(xs):
        if i == ck_i:
            emit("ck", "M5", x, H - 0.042, 0.024, 0.084)
        else:
            n, lay, r, f = next(it)
            emit(n, "M5", x, H - 0.042, 0.024, 0.084)
    open(a.out, "w").write("\n".join(lines) + "\n")
    if a.json:
        json.dump({"lef": a.lef, "lo": a.lo, "hi": a.hi, "ck_x": xs[ck_i], "n_pins": len(north),
                   "pins_total": len(rows), "density_per_um": len(north) / (a.hi - a.lo), "min_gap_um": min(gaps)},
                  open(a.json, "w"), indent=1)
    print(f"wrote {a.out}: {len(rows)} pins, N {len(north)} over {a.lo:g}-{a.hi:g}, ck at {xs[ck_i]:.3f}, min gap {min(gaps):.3f}")


if __name__ == "__main__":
    main()
