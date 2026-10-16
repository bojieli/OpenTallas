#!/usr/bin/env python3
"""BF static front c10 pin plan (S-ELEM-PQ/BF 2026-10-16; VIS-ROM audit of c9: W/E buses 776 pins each packed into the
middle 37 % of the face at 10.4 pins/um, the 1,024-pin N bus 10.4 pins/um on M5 alone, clock entry at the SW corner).

Reads the c9 die-granted plan (physical/ref_tile_specs/s81_bf_native_1015/static_pins/pin_request.json) and keeps every
pin's FACE and the ORDER of the pins along each face (monotone re-spacing only, so the abutting bf_col faces re-pin by
the same order-preserving stretch), then:
  W / E (c0 / c1): spread evenly over the whole face on M4 (track pitch 0.048, offset 0.036);
  N (xb data) and S (x0 / x1 / cfg / f_prog / xb control / status): spread evenly over the whole face, alternating
      M3 (pitch 0.036, offset 0.009) / M5 (pitch 0.048, offset 0.012), so each layer carries half the face density;
  clocks: ck and io_clk enter at the centre of --clock-face (S: x = W/2; W: y = H/2), two tracks apart, with a
      clear keep-gap of --clock-gap um either side.
Usage: bf_static_front_pins_c10.py OUT_DIR --width W [--clock-face S|W] [--margin UM]
"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "physical/ref_tile_specs/s81_bf_native_1015/static_pins/pin_request.json"
H = 198.72
PITCH = {"M3": 0.036, "M4": 0.048, "M5": 0.048}
OFF = {"M3": 0.009, "M4": 0.036, "M5": 0.012}
SIZE = {"M3": (0.018, 0.144), "M5": (0.024, 0.192), "M4": (0.192, 0.024)}
CLOCKS = ("ck", "io_clk")


def track(v, layer, lo, hi):
    p, o = PITCH[layer], OFF[layer]
    t = round((v - o) / p) * p + o
    while t < lo:
        t += p
    while t > hi:
        t -= p
    return round(t, 4)


def spread(names, lo, hi, layers, used):
    """evenly over [lo, hi], each pin on its layer's track, no two pins of one layer closer than 2 tracks"""
    n = len(names)
    out = {}
    step = (hi - lo) / max(n, 1)
    for i, nm in enumerate(names):
        ly = layers[i % len(layers)]
        v = track(lo + (i + 0.5) * step, ly, lo, hi)
        while any(abs(v - u) < 2 * PITCH[ly] - 1e-6 for u in used.setdefault(ly, [])):
            v = round(v + PITCH[ly], 4)
        used[ly].append(v)
        out[nm] = (ly, v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--width", type=float, required=True)
    ap.add_argument("--clock-face", choices=("S", "W"), default="S")
    ap.add_argument("--margin", type=float, default=2.16)
    ap.add_argument("--clock-gap", type=float, default=1.0)
    a = ap.parse_args()
    W = a.width
    req = json.loads(SRC.read_text())
    pins = req["pins"]
    face = {}
    for nm, p in pins.items():
        x, y = float(p["x"]), float(p["y"])
        f = "W" if x == 0 and 0 < y < H else "E" if x > 50 and 0 < y < H else "S" if y == 0 else "N"
        face[nm] = (f, x if f in "NS" else y)
    plan = {}
    for f in "NSEW":
        names = [nm for nm in sorted(pins, key=lambda n: face[n][1]) if face[nm][0] == f and nm not in CLOCKS]
        if not names:
            continue
        layers = ["M4"] if f in "EW" else ["M5", "M3"]
        span = W if f in "NS" else H
        lo, hi = a.margin, span - a.margin
        used = {}
        if f == a.clock_face:
            # clocks at the face centre, the bus split around a keep-gap
            c = span / 2
            ly = "M5" if f == "S" else "M4"
            ck = track(c - PITCH[ly], ly, lo, hi)
            io = track(c + PITCH[ly], ly, lo, hi)
            plan["ck"], plan["io_clk"] = (f, ly, ck), (f, ly, io)
            left = names[: len(names) // 2]
            right = names[len(names) // 2:]
            for part, (l0, h0) in ((left, (lo, c - a.clock_gap)), (right, (c + a.clock_gap, hi))):
                for nm, (lyr, v) in spread(part, l0, h0, layers, used).items():
                    plan[nm] = (f, lyr, v)
        else:
            for nm, (lyr, v) in spread(names, lo, hi, layers, used).items():
                plan[nm] = (f, lyr, v)
    assert set(plan) == set(pins), set(pins) ^ set(plan)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tcl = [f"# BF static front c10 pins (tools/s81/bf_static_front_pins_c10.py --width {W} --clock-face {a.clock_face}): "
           "c9 faces and per-face bit order kept, every face spread evenly, N/S alternating M5/M3, clocks at the "
           f"{a.clock_face}-face centre."]
    newreq = {"schema": "opentallas.s81.static_bf_pin_request.v1",
              "status": "SLOT_CHANGE_REQUEST_C10 (die-owned; see el1011-s81die.log)",
              "top": req["top"], "outline_um": [W, H], "basis": str(SRC.relative_to(ROOT)), "pins": {}}
    dens = {}
    for nm in sorted(plan):
        f, ly, v = plan[nm]
        x, y = {"W": (0.0, v), "E": (W, v), "S": (v, 0.0), "N": (v, H)}[f]
        w, h = SIZE[ly]
        tcl.append(f"place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.6f} {y:.6f}}} -pin_size {{{w} {h}}} "
                   "-force_to_die_boundary")
        newreq["pins"][nm] = {"layer": ly, "x": round(x, 4), "y": round(y, 4), "w": str(w), "h": str(h),
                              "source_pin": pins[nm].get("source_pin"), "face": f}
        dens.setdefault(f, []).append(v)
    for f, vs in dens.items():
        span = W if f in "NS" else H
        newreq.setdefault("face_density_pins_per_um", {})[f] = round(len(vs) / (max(vs) - min(vs) + 1e-9), 2)
    (out / "pins.tcl").write_text("\n".join(tcl) + "\n")
    (out / "pin_request.json").write_text(json.dumps(newreq, indent=1) + "\n")
    print(json.dumps({"width": W, "clock": {k: plan[k] for k in CLOCKS}, "density": newreq["face_density_pins_per_um"],
                      "count": {f: len(v) for f, v in dens.items()}}))


if __name__ == "__main__":
    main()
