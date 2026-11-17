#!/usr/bin/env python3
"""lef_pin_obs_trim: cut hard-core view OBS metal back from the signal pin boxes it touches.

Class (FABLE-FIX-HEAD-TIMING 11-16, hd_host_e he3/he4, 26 of 30 route DRC markers): a core view exports its internal
routing as detailed OBS rectangles.  Where the internal wire of a pin's own net is exported as an OBS rectangle that
TOUCHES the pin rectangle on the same layer (ot_s81hd_he_epc M7: 13 of 555 pins, OBS starts at the pin end y 0.192;
the other pins have 0.261 um of clearance), the detailed router sees foreign metal at the end of the wire it lands on the
pin and reports Lef58EolKeepOut / Metal Spacing against the instance.  In the flat layout that metal is the same net.

Fix (view only, the core is not touched): every OBS rectangle that touches a signal pin rectangle on the same layer is
replaced by what is left of it outside the pin rectangle grown by --clear um (default 0.261, the clearance the clean
pins of the same view have).  OBS that does not touch a pin is not changed; pins are not changed.  An OBS rectangle that contains the whole pin
rectangle (blanket layer block) is left alone.

  lef_pin_obs_trim.py IN.lef OUT.lef [--clear 0.261] [--layers M7,M6] [--check]
--check: exit 1 if IN.lef has any touching OBS (no file written).
Prints: LEF_PIN_OBS_TRIM <macro> layer <L> pins <n> obs_cut <k> pieces <p>
"""
import argparse
import re
import sys

Q = 10000  # 0.1 nm grid


def q(s):
    return int(round(float(s) * Q))


def fmt(v):
    s = "%.4f" % (v / Q)
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


RECT = re.compile(r"^(\s*)RECT\s+(?:MASK\s+\d+\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;\s*$")
LAYER = re.compile(r"^\s*LAYER\s+(\S+)")


def touches(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def subtract(b, r):
    """b minus r as up to four rectangles (zero-area pieces dropped)."""
    out = []
    if b[3] > r[3]:
        out.append((b[0], max(b[1], r[3]), b[2], b[3]))
    if b[1] < r[1]:
        out.append((b[0], b[1], b[2], min(b[3], r[1])))
    y1, y2 = max(b[1], r[1]), min(b[3], r[3])
    if y2 > y1:
        if b[0] < r[0]:
            out.append((b[0], y1, min(b[2], r[0]), y2))
        if b[2] > r[2]:
            out.append((max(b[0], r[2]), y1, b[2], y2))
    return [p for p in out if p[2] > p[0] and p[3] > p[1]]


def process(lines, clear, layers=None):
    """Return (new_lines, stats); stats = {(macro, layer): [pins, obs_cut, pieces]}."""
    out, stats = [], {}
    i, n = 0, len(lines)
    macro = None
    pins = {}          # layer -> [(rect, pin)]
    while i < n:
        ln = lines[i]
        m = re.match(r"^\s*MACRO\s+(\S+)", ln)
        if m:
            macro, pins = m.group(1), {}
            # first pass over this macro: signal pin rectangles
            j, pin, sig, lay = i + 1, None, True, None
            while j < n and not re.match(r"^\s*END\s+%s\s*$" % re.escape(macro), lines[j]):
                t = lines[j]
                mp = re.match(r"^\s*PIN\s+(\S+)", t)
                if mp:
                    pin, sig, lay = mp.group(1), True, None
                elif pin and re.match(r"^\s*USE\s+(POWER|GROUND)", t):
                    sig = False
                elif pin and re.match(r"^\s*END\s+%s\s*$" % re.escape(pin), t):
                    pin = None
                elif re.match(r"^\s*OBS\b", t):
                    pin = None
                elif pin:
                    ml = LAYER.match(t)
                    if ml:
                        lay = ml.group(1)
                    mr = RECT.match(t)
                    if mr and lay:
                        pins.setdefault(lay, []).append((tuple(q(x) for x in mr.groups()[1:]), pin, sig))
                j += 1
            out.append(ln)
            i += 1
            continue
        if macro and re.match(r"^\s*OBS\b", ln):
            out.append(ln)
            i += 1
            lay = None
            while i < n and not re.match(r"^\s*END\s*$", lines[i]):
                t = lines[i]
                ml = LAYER.match(t)
                if ml:
                    lay = ml.group(1)
                mr = RECT.match(t)
                cand = pins.get(lay, []) if (layers is None or lay in layers) else []
                if mr and cand:
                    b = tuple(q(x) for x in mr.groups()[1:])
                    # a blanket block that contains the whole pin rectangle is the standard covered-pin form: not this class
                    hit = [(r, p) for r, p, s in cand if s and touches(b, r) and not contains(b, r)]
                    if hit:
                        pieces = [b]
                        for r, _p in hit:
                            g = (r[0] - clear, r[1] - clear, r[2] + clear, r[3] + clear)
                            pieces = [x for pc in pieces for x in subtract(pc, g)]
                        st = stats.setdefault((macro, lay), [set(), 0, 0])
                        st[0].update(p for _r, p in hit)
                        st[1] += 1
                        st[2] += len(pieces)
                        for pc in pieces:
                            out.append("%sRECT %s %s %s %s ;\n" % (mr.group(1), fmt(pc[0]), fmt(pc[1]), fmt(pc[2]), fmt(pc[3])))
                        i += 1
                        continue
                out.append(t)
                i += 1
            continue
        out.append(ln)
        i += 1
    return out, stats


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--clear", type=float, default=0.261)
    ap.add_argument("--layers")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    lines = open(a.src).read().splitlines(keepends=True)
    new, stats = process(lines, q(a.clear), set(a.layers.split(",")) if a.layers else None)
    for (macro, lay), (pn, k, p) in sorted(stats.items()):
        print("LEF_PIN_OBS_TRIM %s layer %s pins %d obs_cut %d pieces %d" % (macro, lay, len(pn), k, p))
    if not stats:
        print("LEF_PIN_OBS_TRIM no OBS rectangle touches a signal pin")
    if a.check:
        return 1 if stats else 0
    if not a.dst:
        ap.error("OUT.lef required without --check")
    open(a.dst, "w").write("".join(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
