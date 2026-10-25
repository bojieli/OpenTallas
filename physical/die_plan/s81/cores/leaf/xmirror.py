#!/usr/bin/env python3
"""S81/LEAFPLAN 10-24 (coordinator ruling (b), S81-CORES 18:59 PARKED): x-mirrored PIN VARIANTS of the leaf cores vn,
vq and vs as new core views.  An MY orient of the closed / re-pinned view cannot be placed: the V-layer pins (M3 pitch
0.036, M5 pitch 0.048) land 0.018 / 0.024 um off the plan tracks after x' = W - x and the two layers have no common
sub-lattice shift (gen_plan_v4 mirrored() SystemExit).  A variant view is the same module / RTL / port list with its pins
at x' = W - x, every V-layer pin snapped to the plan track of its layer (all pins of one layer move the same way; the
next free track on a collision), H-layer pins (M4 on the E / W faces) keep their y track and swap faces exactly.
Sources: vn = the closed view's plan pin table (inputs/core_pins/ot_s81sl_vn.json), vq / vs = the leaf re-pins
(inputs/core_pins/ot_s81sl_{vq,vs}_lfp.json, cores/leaf/repin.py).  Constant pins (OWNER DECISION 8) go through
drop_const_pins.drop().  Writes inputs/core_pins/<mod>_xm.json (plan pin table) and cores/leaf/lef/<mod>_xm.lef (stub
abstract: pins + OBS M1-M7, MACRO = the RTL module like the _lfp stubs; the closed variant needs its own GDS cell name,
e.g. <mod>_xm, at kit time).  Re-run after repin.py.
usage (repo root): python3 physical/die_plan/s81/cores/leaf/xmirror.py"""
import hashlib, json, os, sys
D = "physical/die_plan/s81"
sys.path.insert(0, os.path.join(D, "cores/leaf"))
sys.path.insert(0, D)
import repin                 # noqa: E402  (track grid, pin shapes, stub LEF writer, LEF directions)
import drop_const_pins       # noqa: E402

# variant -> (source plan pin table, LEF the directions come from, outline W x H)
SRC = {   # vn: superseded by the split views (cores/leaf/split.py builds vn_a / vn_b / ve_s / ve_m and their _xm)
    "ot_s81sl_vq": ("ot_s81sl_vq_lfp", "physical/ref_tile/s81sl_vq/views/ot_s81sl_vq/ot_s81sl_vq.lef", (172.8, 129.6)),
    "ot_s81sl_vs": ("ot_s81sl_vs_lfp", "physical/ref_tile/s81sl_vs/views/ot_s81sl_vs/ot_s81sl_vs.lef", (172.8, 172.8)),
}
VLAY = ("M3", "M5", "M7")
GRID = dict(repin.LAY, M7=(0.064, 0.032))


def on_track(L, x):
    p, o = GRID[L]
    r = (x + repin.OFF[0] - o) % p
    return min(r, p - r) < 1e-4


def snap(L, x, used, W):
    """nearest-below plan track of layer L to x (then the next free one either side) in [edge, W - edge]."""
    p, o = GRID[L]
    k = round((x + repin.OFF[0] - o) / p - 0.5 + 1e-6)          # floor-ish: the track just below x' (or at x')
    for dk in (0, 1, -1, 2, -2, 3, -3, 4, -4):
        c = round(o + (k + dk) * p - repin.OFF[0], 4)
        if c not in used and 0.0 < c < W:
            used.add(c)
            return c
    raise SystemExit("xmirror: no free %s track near x %.4f" % (L, x))


def mirror(mod):
    src, lef_src, (W, H) = SRC[mod]
    j = json.load(open(os.path.join(D, "inputs/core_pins/%s.json" % src)))
    used = {}
    pins, moved = [], 0
    for p in sorted(j["pins"], key=lambda q: (q["layer"], -q["x"])):    # V pins snapped in mirrored x order
        x = round(W - p["x"], 4)
        L = p["layer"]
        if L in VLAY:
            face = "N" if p["y"] > H / 2 else "S"
            x2 = snap(L, x, used.setdefault((L, face), set()), W)
            moved = max(moved, abs(x2 - x))
            x = x2
        pins.append(dict(name=p["name"], layer=L, x=x, y=p["y"]))
    bad = [q for q in pins if q["layer"] in VLAY and not on_track(q["layer"], q["x"])]
    if bad:
        raise SystemExit("xmirror %s: %d V pins off track" % (mod, len(bad)))
    pins.sort(key=lambda q: q["name"])
    lp = os.path.join(D, "cores/leaf/lef/%s_xm.lef" % mod)
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    open(lp, "w").write(repin.lef(mod, W, H, pins, repin.lef_dirs(lef_src)))
    out = dict(module=mod, lef=lp,
               source="S81/LEAFPLAN 10-24 x-mirror pin variant (cores/leaf/xmirror.py) of inputs/core_pins/%s.json "
                      "(%s): same module / ports, %gx%g, pins x' = W - x, V-layer pins snapped to the plan tracks "
                      "(max shift %.3f um)" % (src, j.get("lef"), W, H, moved),
               pinhash=hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12], pins=pins)
    n = drop_const_pins.drop(out, lp)
    jp = os.path.join(D, "inputs/core_pins/%s_xm.json" % mod)
    json.dump(out, open(jp, "w"), indent=0)
    print("wrote %s %s: %d pins (%d const dropped), max V snap %.3f um" % (jp, lp, len(pins), n, moved))


def main():
    for mod in SRC:
        mirror(mod)


if __name__ == "__main__":
    main()
