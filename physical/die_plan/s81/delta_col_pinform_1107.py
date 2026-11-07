#!/usr/bin/env python3
"""S81 plan event COL-PINFORM-1107 (S81-COLH10-1, COORD 00:25 render smells 2/3/6/7): frame_int windows of the col
stack r0/r1/r2 move from the low end of the face to the column of the macros they serve.

Why: gen_plan_v4 packs the N/S frame_int runs from local x 6 at ALLOC_PPU 4.6 pins/um, with no relation to the logic.
In col_h10 the big bus (r0->r1 1264 bits, r1->r2 1230 bits) is driven by u_t<k> (x 389-473) + u_t<k>__payload
(x 648-734) and received by u_e<k> (bf_front_roots, x 518-635) or the next u_t; the window was x 6-277, so about 2200
wires ran 400-700 um along the face and through the 23-um slots beside the bf macros (channel_v 1.26 at x 504-514).
Over the macros only M6/M7 are free, so vertical runs on M7 straight over the band are the cheap path.

What: type-frame windows, every col_h10 instance (MX: die x = origin + x; R180: die x = origin + W - x; lane order
unchanged).  r0->r1 big bus sits on the u_e input column (its x0/x1 pins are on the S face, x 543-632).  r1->r2 big bus has
two segments: t bits over x 384-518, payload bits over the free slot + x 635-800; not over the bf_front M5 ceiling, where
flops in the slot had to run along the 16-um face strip (view 05:12).  The small buses go east of the macro band, x > 1143,
where every layer is free, not over bf_col3_c (M1-M6 OBS: M7 only).  Bit order, widths, faces and layers are unchanged, so RTL, bind and LEC are unchanged.  PIN CYCLES: 0.
    python3 -I delta_col_pinform_1107.py PLAN [--family col_h10] [--dry]        (cwd = repo root)
"""
import json
import math
import re
import sys
from fractions import Fraction

sys.path.insert(0, "tools/die_plan")
import schema as S  # noqa: E402

# window = (lo, hi) in the TYPE frame; big bus centred on the t + payload + e column, small bus just east of it
BIG_R0R1 = (470.4, 710.4)
BIG_R1R2 = ((384.0, 518.4), (635.52, 800.64))
SMALL_R0R1 = (1152.0, 1214.4)
SMALL_R1R2 = (1152.0, 1238.4)
SNAP = 0.192


def even_window(lo, hi, layers, TR):
    """snap + keep every layer's k0 + k1 even (mirror-invariant pin table), as gen_plan_v4 does"""
    q0, q1 = math.ceil(lo / SNAP - 1e-6), math.floor(hi / SNAP + 1e-6)
    lo_, hi_ = q0 * SNAP, q1 * SNAP
    for d in range(0, 400):
        h2 = hi_ - d * 0.004
        if all((math.ceil((lo_ - TR[l][1]) / TR[l][0] - 1e-9) + math.floor((h2 - TR[l][1]) / TR[l][0] + 1e-9)) % 2 == 0
               for l in layers):
            return round(lo_, 3), round(h2, 3)
    raise SystemExit(f"no even-parity window for {lo} {hi}")


def main():
    plan = sys.argv[1]
    fam = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else "col_h10"
    dry = "--dry" in sys.argv
    txt = open(plan).read()
    p = json.loads(txt)
    T = p["partition_types"]
    parts = {x["name"]: x for x in p["partitions"]}
    TR = {"M5": (0.048, 0.012), "M7": (0.064, 0.032)}
    plan_layers = S.load(plan).layers if hasattr(S.load(plan), "layers") else None
    if plan_layers:
        TR = {k: (v["pitch_um"], v["offset_um"]) for k, v in plan_layers.items() if k in ("M5", "M7")}
    lines = txt.split("\n")
    idx_type = {}
    for i, l in enumerate(lines):
        m = re.match(r'\s*"(%s[A-Za-z0-9_]*)": \{\s*$' % fam, l)
        if m and m.group(1) in T:
            idx_type.setdefault(m.group(1), i)
    idx_port = {}
    for i, l in enumerate(lines):
        m = re.match(r'\s*"id": "(fi_[A-Za-z0-9_]+)",?\s*$', l)
        if m:
            idx_port.setdefault(m.group(1), i)

    def set_window(i, new):
        j = i
        while '"window_um"' not in lines[j]:
            j += 1
            assert j - i < 60, ("no window near line", i)
        if re.search(r'"window_um": \[\s*$', lines[j]):
            lines[j + 1] = re.sub(r"[\d.]+", str(new[0]), lines[j + 1], count=1)
            lines[j + 2] = re.sub(r"[\d.]+", str(new[1]), lines[j + 2], count=1)
        else:
            lines[j] = re.sub(r'("window_um": \[)[^\]]*\]', lambda m: f"{m.group(1)}{new[0]},{new[1]}]", lines[j])

    changed = dict(ports=0, buses=0, types=set())
    wins = {}
    for pt in p["ports"]:
        if not pt["id"].startswith("fi_"):
            continue
        sp, dp = parts.get(pt["src"]["part"]), parts.get(pt["dst"]["part"])
        if not sp or not sp["type"].startswith(fam):
            continue
        assert dp["type"].startswith(fam), pt["id"]
        stack = "r0r1" if pt["id"].rsplit("__", 1)[0].endswith(("r0r1", "r1r0")) else "r1r2"
        big = pt["width"] >= 1000
        W = T[sp["type"]]["outline_um"][0]
        ox, orient = sp["origin_um"][0], sp["orient"]

        def die(win):
            lo, hi = even_window(*win, pt["layers"], TR)
            if orient in ("MX", "R0"):
                return [round(ox + lo, 3), round(ox + hi, 3)], (lo, hi)
            if orient in ("R180", "MY"):
                return [round(ox + W - hi, 3), round(ox + W - lo, 3)], (lo, hi)
            raise SystemExit(f"orient {orient} {pt['id']}")

        i = idx_port[pt["id"]]
        if big and stack == "r1r2":
            n = S.port_pins_count(pt)
            a0, t0 = die(BIG_R1R2[0])
            a1, t1 = die(BIG_R1R2[1])
            new = [min(a0[0], a1[0]), max(a0[1], a1[1])]
            lo, hi = t0[0], t1[1]
            n0 = 615
            set_window(i, new)
            j = i
            while '"window_um"' not in lines[j]:
                j += 1
            while "]" not in lines[j]:
                j += 1
            ind = re.match(r"\s*", lines[j]).group(0)
            had = lines[j].rstrip().endswith(",")
            lines[j] = lines[j].rstrip().rstrip(",") + ","
            lines[j] += "\n" + ind + '"segments": ' + json.dumps(
                [{"pins": n0, "window_um": a0}, {"pins": n - n0, "window_um": a1}]) + ("," if had else "")
        else:
            win = BIG_R0R1 if big else (SMALL_R0R1 if stack == "r0r1" else SMALL_R1R2)
            new, (lo, hi) = die(win)
            set_window(i, new)
        changed["ports"] += 1
        for side, part in (("src", sp), ("dst", dp)):
            wins[(part["type"], pt[side]["bus"])] = [lo, hi]
    for (tn, bus), new in sorted(wins.items()):
        i = idx_type[tn]
        j = i
        while f'"name": "{bus}"' not in lines[j]:
            j += 1
            assert j - i < 400, (tn, bus)
        set_window(j, new)
        changed["buses"] += 1
        changed["types"].add(tn)
    out = "\n".join(lines)
    q = json.loads(out)
    # only windows differ
    for a, b in ((p, q),):
        for pt0, pt1 in zip(a["ports"], b["ports"]):
            d = {k for k in set(pt0) | set(pt1) if pt0.get(k) != pt1.get(k)}
            assert d <= {"window_um", "segments"}, (pt0["id"], d)
        assert a["lanes"] == b["lanes"] and a["clock"] == b["clock"]
    print("COL_PINFORM", fam, "ports", changed["ports"], "buses", changed["buses"], "types", len(changed["types"]),
          BIG_R0R1, BIG_R1R2, SMALL_R0R1, SMALL_R1R2)
    if not dry:
        open(plan, "w").write(out)


if __name__ == "__main__":
    main()
