#!/usr/bin/env python3
"""lef_pin_narrow: narrow a hard-view signal pin PORT rect that is wider than its layer's wire width, on a layer the view
blankets with OBS, to the wire width at the on-track centre inside the same signed metal (FLOW-OBS-GCELL-R2 11-21, the
S81-BKSEL-R6 DRT-0073 class: a 0.048-um M5 clock pin under the blanket OBS has no TritonRoute access point; the 0.024-um
on-track centre of the same metal has).  LEF-only: the narrowed rect is a subset of the original, so the parent never
lands outside real child metal; netlist, Liberty, LEC untouched.

Track centre: the across-track residue (centre mod pitch) shared by most wire-width pins of that layer in the same macro;
the narrowed centre is the on-residue position nearest the original centre that keeps the rect inside the original.  A
pin with no such position, with several rects on the layer, or on a layer without a blanket OBS is left alone.

  narrow_text(text) -> (new_text, changes)      changes: [{macro, pin, layer, old, new}] (um strings as written)
  CLI: lef_pin_narrow.py IN.lef [OUT.lef]       prints the changes as JSON; writes OUT when given"""
import json
import re
import sys
from collections import Counter, defaultdict

W = {"M2": 18, "M3": 18, "M4": 24, "M5": 24, "M6": 32, "M7": 32}
P = {"M2": 36, "M3": 36, "M4": 48, "M5": 48, "M6": 64, "M7": 64}
VERT = {"M3", "M5", "M7"}
BLANKET_FRAC = 0.5
RECT = re.compile(r"^(\s*RECT\s+)(\S+)\s+(\S+)\s+(\S+)\s+(\S+)(\s*;.*)$")


def _nm(v):
    return int(round(float(v) * 1000))


def narrow_text(text):
    lines = text.split("\n")
    changes = []
    i = 0
    while i < len(lines):
        m = re.match(r"^MACRO (\S+)\s*$", lines[i])
        if not m:
            i += 1
            continue
        name, start = m.group(1), i
        j = i + 1
        while j < len(lines) and not re.match(r"^END " + re.escape(name) + r"\s*$", lines[j]):
            j += 1
        _macro(lines, start, j, name, changes)
        i = j + 1
    return "\n".join(lines), changes


def _macro(lines, a, b, name, changes):
    area, obs = 0, defaultdict(int)
    pins = []            # (pin, layer, line index, x0, y0, x1, y1, n rects of pin on that layer)
    k = a
    while k < b:
        ln = lines[k]
        s = re.match(r"^\s*SIZE\s+(\S+)\s+BY\s+(\S+)", ln)
        if s:
            area = _nm(s.group(1)) * _nm(s.group(2))
        pm = re.match(r"^\s*PIN\s+(\S+)\s*$", ln)
        if pm:
            pn, e = pm.group(1), k + 1
            while e < b and not re.match(r"^\s*END\s+" + re.escape(pn) + r"\s*$", lines[e]):
                e += 1
            body = lines[k:e]
            if not any(re.search(r"\bUSE\s+(POWER|GROUND)\b", x) for x in body):
                lay, rr = None, defaultdict(list)
                for q in range(k + 1, e):
                    t = lines[q].split()
                    if t and t[0] == "LAYER":
                        lay = t[1]
                    else:
                        r = RECT.match(lines[q])
                        if r and lay in W:
                            rr[lay].append((q,) + tuple(_nm(r.group(c)) for c in (2, 3, 4, 5)))
                for lay, lst in rr.items():
                    for it in lst:
                        pins.append((pn, lay) + it + (len(lst),))
            k = e
            continue
        if re.match(r"^\s*OBS\s*$", ln):
            lay = None
            k += 1
            while k < b and not re.match(r"^\s*END\s*$", lines[k]):
                t = lines[k].split()
                if t and t[0] == "LAYER":
                    lay = t[1]
                else:
                    r = RECT.match(lines[k])
                    if r and lay:
                        x0, y0, x1, y1 = (_nm(r.group(c)) for c in (2, 3, 4, 5))
                        obs[lay] = max(obs[lay], (x1 - x0) * (y1 - y0))
                k += 1
        k += 1
    if not area:
        return
    blanket = {l for l, v in obs.items() if v >= BLANKET_FRAC * area}
    res = defaultdict(Counter)
    for pn, lay, q, x0, y0, x1, y1, n in pins:
        lo, hi = (x0, x1) if lay in VERT else (y0, y1)
        if hi - lo == W[lay]:
            res[lay][((lo + hi) // 2) % P[lay]] += 1
    for pn, lay, q, x0, y0, x1, y1, n in pins:
        lo, hi = (x0, x1) if lay in VERT else (y0, y1)
        w, p = W[lay], P[lay]
        if lay not in blanket or n != 1 or hi - lo <= w or not res[lay]:
            continue
        r0 = res[lay].most_common(1)[0][0]
        c0 = (lo + hi) / 2.0
        best = None
        base = int((c0 - r0) // p) * p + r0
        for c in (base - p, base, base + p, base + 2 * p):
            if lo <= c - w // 2 and c + w // 2 <= hi and (best is None or abs(c - c0) < abs(best - c0)):
                best = c
        if best is None:
            continue
        nlo, nhi = best - w // 2, best + w // 2
        r = RECT.match(lines[q])
        old = " ".join(r.group(c) for c in (2, 3, 4, 5))
        f = [r.group(c) for c in (2, 3, 4, 5)]          # unchanged coordinates keep their text
        if lay in VERT:
            f[0], f[2] = "%.3f" % (nlo / 1000.0), "%.3f" % (nhi / 1000.0)
        else:
            f[1], f[3] = "%.3f" % (nlo / 1000.0), "%.3f" % (nhi / 1000.0)
        lines[q] = r.group(1) + " ".join(f) + r.group(6)
        changes.append(dict(macro=name, pin=pn, layer=lay, old=old, new=" ".join(f)))


def main(argv):
    text = open(argv[1]).read()
    new, ch = narrow_text(text)
    print(json.dumps(ch, indent=1))
    if len(argv) > 2:
        open(argv[2], "w").write(new)


if __name__ == "__main__":
    main(sys.argv)
