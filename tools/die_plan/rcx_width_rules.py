#!/usr/bin/env python3
"""CLOCK-128-R6: width-characterised OpenRCX rules for the ASAP7 M8/M9 clock NDR (0.16 / 0.32 um).

Problem (R5, probe CHECKED): flow/platforms/asap7/rcx_patterns.rules carries ONE width entry (0.04 um) for M8/M9 and
OpenRCX uses that entry's per-um R and per-um C for any wider wire: a 0.16-um or 0.32-um wire extracts the 0.04-um
R (8.45 / 8.90 ohm/um, 4x / 8x too high) and the 0.04-um C at its spacing (no area-cap growth with width).

Method (provenance in the output json):
  R  : sheet resistance from the rules' own 0.04-um entry, R_sq = r(0.04) x 0.04, scaled R(w) = R_sq / w.  No
       size-effect credit for the wider wire (bulk-like resistivity would be lower), so R(w) is an upper bound.
  C  : 2-D field solver (fd2d.py, finite-volume Laplace, homogeneous eps_r) calibrated on the rules' own 0.04-um M8/M9
       tables: eps_r, metal thickness and the gaps to the M7 / M9 planes are fitted to OVER 7 UNDER 9, OVER 7 and
       UNDER 9 (M8) and OVER 8 (M9); the plane gap of every other OVER k is fitted per k.  New width entry value =
       rules value at 0.04 x solver(W) / solver(0.04) for the same pattern and spacing (cc and fringe separately), so
       the solver supplies only the WIDTH dependence and the rules keep their own absolute calibration.
  DIAGUNDER entries are copied unchanged (diagonal coupling to an offset upper wire, width-insensitive to first order).

Usage:  rcx_width_rules.py calibrate OUT.json          (fit geometry, ~1 min)
        rcx_width_rules.py write RULES_IN CAL.json RULES_OUT [--widths 0.16]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

W0 = 0.04
LAYERS = (8, 9)


# ------------------------------------------------------------------ rules file parsing
def parse(text):
    """-> list of blocks: ('raw', lines) or ('sec', header, width_line, [(subhdr, [rows])...])"""
    return text.split("\n")


def sections(lines):
    """yield (start, end, name) of every 'Metal N KIND' section that has a 'WIDTH Table' line, N in LAYERS"""
    heads = [i for i, l in enumerate(lines) if re.match(r"^Metal \d+ [A-Z]+$", l)]
    heads.append(len(lines))
    for a, b in zip(heads[:-1], heads[1:]):
        m = re.match(r"^Metal (\d+) ([A-Z]+)$", lines[a])
        yield a, b, int(m.group(1)), m.group(2)


def dist_blocks(lines, a, b):
    """[(hdr_index, label, rows)] inside one section: label = sub header 'Metal 8 OVER 7 UNDER 9' etc."""
    out = []
    i = a + 1
    while i < b:
        l = lines[i]
        if re.match(r"^Metal \d+ ", l) and i + 1 < b and lines[i + 1].startswith("DIST count"):
            j = i + 2
            rows = []
            while not lines[j].startswith("END DIST"):
                rows.append([float(v) for v in lines[j].split()])
                j += 1
            out.append((i, l, rows, j))
            i = j + 1
        else:
            i += 1
    return out


# ------------------------------------------------------------------ geometry model
def geom_for(cal, layer, label):
    """(below_gap or None, above_gap or None, t) of a pattern label 'Metal 8 OVER 7 UNDER 9' / 'Metal 8 UNDER 9' ..."""
    L = cal["layers"][str(layer)]
    ov = re.search(r"OVER (\d+)", label)
    un = re.search(r"UNDER (\d+)", label)
    below = L["gap_over"][ov.group(1)] if ov else None
    above = None
    if un and un.group(1) in L["gap_under"]:
        above = L["gap_under"][un.group(1)]
    return below, above, L["t"]


def rpersq(rules_text):
    """{layer: sheet resistance ohm/sq} = RESOVER 0 first-row r (kohm/um) x the table's (single) width, M1..M9"""
    lines = rules_text.split("\n")
    out = {}
    for a, b, n, kind in sections(lines):
        if kind != "RESOVER":
            continue
        for _, l, rows, _ in dist_blocks(lines, a, b):
            if l == f"Metal {n} RESOVER 0" and rows and n <= 9:
                w = float(re.search(r"width ([\d.]+)", lines[_dist_line(lines, l)]).group(1))
                out[f"M{n}"] = rows[0][-1] * 1e3 * w
                break
    return out


def _dist_line(lines, label):
    return lines.index(label) + 1


def solve_row(cal, layer, label, w, s, neighbours):
    import fd2d
    below, above, t = geom_for(cal, layer, label)
    return fd2d.pattern(w, t, s, below=below, above=above, neighbours=neighbours, eps_r=cal["eps_r"])


def _table(lines, layer, label):
    for a, b, n, kind in sections(lines):
        if n != layer:
            continue
        for _, l, rows, _ in dist_blocks(lines, a, b):
            if l == label:
                return rows
    raise KeyError(label)


def calibrate(rules_text):
    import fd2d
    import numpy as np
    from scipy.optimize import least_squares
    lines = rules_text.split("\n")
    fit_s = (0.04, 0.08, 0.16, 0.24)
    big_s = 0.48

    def resid_rows(rows, w, t, below, above, eps, scale=1.0):
        r = []
        for row in rows:
            s, cc, fr = row[0], row[1] * 1e3, row[2] * 1e3
            if s in fit_s and cc > 0:
                c2, f2 = fd2d.pattern(w, t, s, below=below, above=above, neighbours=True, eps_r=eps)
                r += [(c2 - cc) / cc, (f2 - fr) / max(fr, 0.01) * scale]
            if abs(s - big_s) < 1e-9 and cc == 0:
                _, f2 = fd2d.pattern(w, t, s, below=below, above=above, neighbours=False, eps_r=eps)
                r += [(f2 - fr) / fr]
        return r

    T_ou = _table(lines, 8, "Metal 8 OVER 7 UNDER 9")
    T_o = _table(lines, 8, "Metal 8 OVER 7")
    T_u = _table(lines, 8, "Metal 8 UNDER 9")
    T9 = _table(lines, 9, "Metal 9 OVER 8")

    def f8(p):
        eps, t, b, a = p
        return (resid_rows(T_ou, W0, t, b, a, eps) + resid_rows(T_o, W0, t, b, None, eps)
                + resid_rows(T_u, W0, t, None, a, eps))
    r8 = least_squares(f8, [3.0, 0.08, 0.1, 0.1], bounds=([1.5, 0.03, 0.02, 0.02], [6.0, 0.3, 0.6, 0.6]),
                       diff_step=1e-3)
    eps, t8, b8, a8 = r8.x

    def f9(p):
        t9, b9 = p
        return resid_rows(T9, W0, t9, b9, None, eps)
    r9 = least_squares(f9, [t8, a8], bounds=([0.03, 0.02], [0.3, 0.6]), diff_step=1e-3)
    t9, b9 = r9.x
    cal = dict(eps_r=float(eps), layers={
        "8": dict(t=float(t8), gap_over={"7": float(b8)}, gap_under={"9": float(a8)}),
        "9": dict(t=float(t9), gap_over={"8": float(b9)}, gap_under={})},
        fit=dict(m8_rms=float(np.sqrt(np.mean(np.square(r8.fun)))), m9_rms=float(np.sqrt(np.mean(np.square(r9.fun))))))
    # plane gap of every other OVER k (one parameter each, eps / t fixed)
    for layer, top in ((8, 6), (9, 7)):
        Lc = cal["layers"][str(layer)]
        prev = Lc["gap_over"][str(top + 1)]
        for k in range(top, -1, -1):
            try:
                rows = _table(lines, layer, f"Metal {layer} OVER {k}")
            except KeyError:
                continue
            if not rows:
                continue
            rk = least_squares(lambda p: resid_rows(rows, W0, Lc["t"], p[0], None, eps, 0.5), [prev * 1.3],
                               bounds=([0.02], [3.0]), diff_step=1e-3)
            Lc["gap_over"][str(k)] = float(rk.x[0])
            cal["fit"][f"m{layer}_over{k}_rms"] = float(np.sqrt(np.mean(np.square(rk.fun))))
            prev = float(rk.x[0])
    return cal


# ------------------------------------------------------------------ rules writer
def widen(rules_text, cal, widths):
    """return (new rules text, provenance dict): every M8/M9 section gains entries for `widths` after the 0.04 one"""
    lines = rules_text.split("\n")
    out = []
    prov = dict(widths=widths, method=__doc__.split("Method")[1].split("Usage")[0].strip(), cal=cal, samples=[])
    cache = {}
    secs = {a: (b, n, kind) for a, b, n, kind in sections(lines)}
    i = 0
    while i < len(lines):
        if i in secs and secs[i][1] in LAYERS:
            b, n, kind = secs[i]
            sec = lines[i:b]
            wl = [k for k, l in enumerate(sec) if l.startswith("WIDTH Table")]
            if not wl or "0 entries" in sec[wl[0]]:
                out += sec
                i = b
                continue
            ws = [float(v) for v in sec[wl[0]].split(":")[1].split()]
            assert ws == [W0], (n, kind, ws)
            sec[wl[0]] = f"WIDTH Table {1 + len(widths)} entries:  " + " ".join(f"{v:g}" for v in [W0] + widths)
            # each sub-block: header, DIST line, rows, END DIST -> append one block per extra width after it
            new = []
            k = 0
            while k < len(sec):
                l = sec[k]
                new.append(l)
                if k + 1 < len(sec) and sec[k + 1].startswith("DIST count") and re.match(r"^Metal \d+ ", l):
                    dl = sec[k + 1]
                    j = k + 2
                    rows = []
                    while not sec[j].startswith("END DIST"):
                        rows.append([float(v) for v in sec[j].split()])
                        j += 1
                    new += sec[k + 1:j + 1]
                    for W in widths:
                        new.append(re.sub(r"width [\d.]+", f"width {W:g}", dl))
                        for row in rows:
                            new.append(" ".join(_fmt(v) for v in _scale_row(kind, n, l, row, W, cal, cache, prov)))
                        new.append("END DIST")
                    k = j + 1
                    continue
                k += 1
            out += new
            i = b
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), prov


def _fmt(v):
    return "0" if v == 0 else f"{v:g}"


def _scale_row(kind, layer, label, row, W, cal, cache, prov):
    if kind == "RESOVER":
        return row[:-1] + [row[-1] * W0 / W]
    s, cc, fr, r = row
    r2 = r * W0 / W
    if kind == "DIAGUNDER":
        return [s, cc, fr, r2]
    nb = cc > 0
    key = (layer, label, s, nb)
    if key not in cache:
        c0, f0 = solve_row(cal, layer, label, W0, s, nb)
        c1, f1 = solve_row(cal, layer, label, W, s, nb)
        cache[key] = (c0, f0, c1, f1)
    c0, f0, c1, f1 = cache[key]
    kc = c1 / c0 if nb and c0 > 0 else 1.0
    kf = f1 / f0 if f0 > 0 else 1.0
    if s in (0.08,) or (not nb and abs(s - 0.48) < 1e-9):
        prov["samples"].append(dict(layer=layer, pattern=label, s=s, W=W, cc_ratio=round(kc, 4), fr_ratio=round(kf, 4),
                                    solver_fF_um=dict(cc0=round(c0, 5), fr0=round(f0, 5), cc1=round(c1, 5),
                                                      fr1=round(f1, 5))))
    return [s, cc * kc, fr * kf, r2]


def main(argv):
    if argv[0] == "calibrate":
        rules = open(argv[1]).read()
        cal = calibrate(rules)
        json.dump(cal, open(argv[2], "w"), indent=1)
        print(json.dumps(cal, indent=1))
    elif argv[0] == "write":
        # 0.16 only: the OpenRCX build of openroad/orfs (26Q3) picks the SECOND width entry for both 0.16 and 0.32
        # wires (probe CLOCK-128-R6: a 0.32 entry is never selected), so a 0.32 entry would be dead data; 8W wires
        # extract with the 0.16 C (under by ~13 %, field solver) -- the die clock NDR is 4W (0.16).
        widths = [0.16]
        if "--widths" in argv:
            widths = [float(v) for v in argv[argv.index("--widths") + 1].split(",")]
        txt, prov = widen(open(argv[1]).read(), json.load(open(argv[2])), widths)
        open(argv[3], "w").write(txt)
        json.dump(prov, open(argv[3] + ".provenance.json", "w"), indent=1)
        print(f"wrote {argv[3]} (+ .provenance.json), {len(prov['samples'])} samples")


if __name__ == "__main__":
    main(sys.argv[1:])
