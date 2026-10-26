#!/usr/bin/env python3
"""pin_template.py -- ONE fixed pin table per hard-core template (TYPE-REDUCE-2, OWNER 2026-10-25 19:53 cause (3)).

Problem: the plan pins a core per slot, so instances of one RTL module carry different pin tables (S81 leaf cores: a
base table + an x-mirrored `_xm` view per module; HBM: one table per instance) and every table is a separate design
to harden and sign off.  A template is placed in every slot from ONE table; only the orientation changes.

Mirror legality.  A vertical-layer pin (N/S faces) at core-frame x sits on a track in the parent when
    origin_x + track_offset_x + x            == o_L  (mod p_L)   for R0 / MX
    origin_x + track_offset_x + W - x        == o_L  (mod p_L)   for MY / R180
For a table whose pins are on the plan lattice (x == o_L - toff + k p_L) the MY form needs
    toff_MY == 2 o_L - toff - W  (mod p_L)          per V layer L
and two layers are usable together only if those residues agree mod gcd(p_L1, p_L2).  ASAP7 M3 (0.036 / 0.009) and
M5 (0.048 / 0.024) never agree (gcd 0.012: 0.018 vs 0.024 -> 0.006 apart), which is why `_xm` views exist.  The fix is
structural: a template's mirrored faces use ONE mirror-compatible V-layer set (default M5 only; M5+M7 also agree mod
0.016), and MY instances take the solved track offset.  H-layer pins (E/W faces) keep y, so MX is always legal.

Commands
  check  --plan P             per module: tables in use, their relation (same / mirror-x / mirror-y / other), the
                              mirror-compatible V-layer sets, and whether the base table is already a template
  make   --plan P --module M  write the template table (V pins of N/S faces moved, order kept, to the nearest free
                              track of the allowed layers, every 2nd track unless the face needs every track) + stub
                              LEF; rewrite every instance of M to the template: base-table instances keep orient,
                              mirror-view instances get orient o*MY and the solved track offset.  Reports per-pin
                              displacement in the parent frame (vs the per-slot table the instance used before).
Read the outputs; nothing is kitted.  Re-kit + GEOM review are owed for every module whose table changes.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

# ASAP7 plan lattice (pitch, offset) in the parent frame -- the S81 leaf core generator (cores/leaf/repin.py LAY) and
# xmirror.py GRID; layers are vertical (x tracks) or horizontal (y tracks)
LATTICE = {"M2": (0.036, 0.018, "H"), "M3": (0.036, 0.009, "V"), "M4": (0.048, 0.024, "H"),
           "M5": (0.048, 0.024, "V"), "M6": (0.064, 0.032, "H"), "M7": (0.064, 0.032, "V")}
EDGE = {"M3": 0.019, "M4": 0.042, "M5": 0.042, "M7": 0.056}
RECT = {"M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084), "M7": (0.032, 0.112)}
FLIP_X = {"R0": "MY", "MY": "R0", "MX": "R180", "R180": "MX"}     # compose with an x mirror


def F(x):
    return Fraction(str(round(float(x), 6)))


def my_offset(layer, toff, W):
    """track offset x an MY instance needs so that layer's pins land on tracks (mod pitch), as Fraction"""
    p, o, _ = LATTICE[layer]
    return (2 * F(o) - F(toff) - F(W)) % F(p)


def compatible(layers, toff, W):
    """-> (ok, offset delta in [0, lcm) to ADD to toff, lcm) for an MY instance using these V layers"""
    res = [(my_offset(L, toff, W), F(LATTICE[L][0])) for L in layers]
    a, m = res[0]
    for b, n in res[1:]:                                   # CRT on rationals (scale to integers in nm/1000)
        s = 1000000
        A, M, B, N = int(a * s), int(m * s), int(b * s), int(n * s)
        g = math.gcd(M, N)
        if (B - A) % g:
            return False, None, None
        l = M // g * N
        k = ((B - A) // g * pow(M // g, -1, N // g)) % (N // g)
        a, m = Fraction(A + k * M, s) % Fraction(l, s), Fraction(l, s)
    return True, (a - F(toff)) % m, m


def on_track(layer, x_parent):
    p, o, _ = LATTICE[layer]
    r = (F(x_parent) - F(o)) % F(p)
    return min(r, F(p) - r) < Fraction(1, 10000)


def face_of(pin, W, H):
    x, y = float(pin["x"]), float(pin["y"])
    d = {"S": y, "N": H - y, "W": x, "E": W - x}
    return min(d, key=d.get)


def relation(a, b, W, H):
    """pin-table relation of b to a: same / mirror-x (x' = W - x) / mirror-y / other (+ fraction that matches)"""
    A = {p["name"]: p for p in a}
    B = {p["name"]: p for p in b}
    if set(A) != set(B):
        return "ports-differ", 0.0
    n = len(A)
    same = sum(abs(A[k]["x"] - B[k]["x"]) < 1e-3 and abs(A[k]["y"] - B[k]["y"]) < 1e-3 for k in A)
    mx = sum(abs(B[k]["x"] - (W - A[k]["x"])) < 0.2 and abs(A[k]["y"] - B[k]["y"]) < 1e-3 for k in A)
    my = sum(abs(B[k]["y"] - (H - A[k]["y"])) < 0.2 and abs(A[k]["x"] - B[k]["x"]) < 1e-3 for k in A)
    best = max((same, "same"), (mx, "mirror-x"), (my, "mirror-y"))
    return best[1], best[0] / max(n, 1)


def tracks(layer, lo, hi, toff):
    p, o, _ = LATTICE[layer]
    k = math.ceil((lo + toff - o) / p - 1e-9)
    out = []
    while True:
        c = round(o + k * p - toff, 4)
        if c > hi:
            return out
        out.append(c)
        k += 1


def make_template(pins, W, H, toff, vlayers=("M5",), margin=4.32):
    """move every V-layer pin of the N / S faces onto the allowed layers' tracks, face order kept, nearest free track
    (every 2nd track; every track if the face needs it).  -> (pins, max shift um)"""
    out, worst = [], 0.0
    by_face = {}
    for p in pins:
        f = face_of(p, W, H)
        if f in "NS" and LATTICE.get(p["layer"], (0, 0, "H"))[2] == "V":
            by_face.setdefault(f, []).append(p)
        else:
            out.append(dict(p))
    for f, ps in by_face.items():
        ps = sorted(ps, key=lambda q: (q["x"], q["name"]))
        slots = []
        for L in vlayers:
            t = tracks(L, margin, W - margin, toff)
            slots += [(c, L) for c in t]
        slots.sort()
        step = 2 if len(slots) // 2 >= len(ps) else 1
        if len(slots) // step < len(ps):
            raise SystemExit(f"pin_template: face {f}: {len(ps)} V pins > {len(slots)} tracks of {vlayers}")
        slots = slots[::step]
        # order-preserving nearest assignment (monotone DP-free greedy: walk pins and slots left to right)
        n, m = len(ps), len(slots)
        j = 0
        for i, p in enumerate(ps):
            # the latest slot index this pin may take so the rest still fit
            hi = m - (n - i)
            best = min(range(j, hi + 1), key=lambda k: abs(slots[k][0] - p["x"]))
            c, L = slots[best]
            j = best + 1
            e = EDGE[L]
            y = H - e if f == "N" else e
            worst = max(worst, abs(c - p["x"]))
            out.append(dict(name=p["name"], layer=L, x=round(c, 4), y=round(y, 4)))
    out.sort(key=lambda q: q["name"])
    return out, worst


def lef_dirs(path):
    d, cur = {}, None
    for ln in Path(path).read_text().splitlines():
        m = re.match(r"\s*PIN\s+(\S+)", ln)
        if m:
            cur = m.group(1)
        m = re.match(r"\s*DIRECTION\s+(\S+)", ln)
        if m and cur:
            d[cur] = m.group(1)
    return d


def lef(macro, W, H, pins, dirs):
    o = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", f"MACRO {macro}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  SIZE {W:.3f} BY {H:.3f} ;"]
    for p in pins:
        w, h = RECT[p["layer"]]
        x0, y0 = p["x"] - w / 2, p["y"] - h / 2
        x0 = min(max(x0, 0.0), W - w)
        y0 = min(max(y0, 0.0), H - h)
        o += [f"  PIN {p['name']}", f"    DIRECTION {dirs.get(p['name'], 'INPUT')} ;", "    USE SIGNAL ;", "    PORT",
              f"      LAYER {p['layer']} ;", f"        RECT {x0:.4f} {y0:.4f} {x0 + w:.4f} {y0 + h:.4f} ;", "    END",
              f"  END {p['name']}"]
    o += ["  OBS", *[f"    LAYER M{i} ;\n      RECT 0 0 {W:.3f} {H:.3f} ;" for i in range(1, 8)], "  END",
          f"END {macro}", "END LIBRARY", ""]
    return "\n".join(o)


def load_pins(pdir, f):
    j = json.loads((pdir / f).read_text())
    return j, (j["pins"] if isinstance(j, dict) else j)


def lef_size(path):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", Path(path).read_text())
    return float(m.group(1)), float(m.group(2))


def uses(plan, module):
    for k, t in plan["partition_types"].items():
        for h in t.get("hard_cores") or []:
            if h.get("module") == module:
                yield k, h


def check(plan, pdir, root):
    mods = {}
    for k, t in plan["partition_types"].items():
        for h in t.get("hard_cores") or []:
            if h.get("pins_file"):
                mods.setdefault(h["module"], {}).setdefault(h["pins_file"], h)
    rep = {}
    for m, tabs in sorted(mods.items()):
        if len(tabs) < 2:
            continue
        files = sorted(tabs, key=lambda f: ("_xm" in f, f))
        h0 = tabs[files[0]]
        try:
            W, H = lef_size(root / h0["lef"])
        except (OSError, AttributeError, KeyError):
            W, H = [float(v) for v in h0.get("outline_um")]
        _, base = load_pins(pdir, files[0])
        toff = float((h0.get("track_offset_um") or [0, 0])[0])
        vl = sorted({p["layer"] for p in base if LATTICE.get(p["layer"], (0, 0, "H"))[2] == "V"
                     and face_of(p, W, H) in "NS"})
        ok, delta, per = compatible(vl, toff, W) if vl else (True, Fraction(0), None)
        rel = {f: relation(base, load_pins(pdir, f)[1], W, H) for f in files[1:]}
        rep[m] = dict(tables=files, size=[W, H], ns_vlayers=vl, base_mirror_legal=ok,
                      relation={f: [r, round(x, 3)] for f, (r, x) in rel.items()},
                      m5_offset_delta=float(compatible(["M5"], toff, W)[1]))
    return rep


def make(plan, pdir, root, module, vlayers, out_stem=None):
    ent = list(uses(plan, module))
    files = sorted({h["pins_file"] for _, h in ent}, key=lambda f: ("_xm" in f, f))
    base_f = files[0]
    h0 = next(h for _, h in ent if h["pins_file"] == base_f)
    W, H = lef_size(root / h0["lef"])
    toff = float((h0.get("track_offset_um") or [0, 0])[0])
    bj, base = load_pins(pdir, base_f)
    ok, delta, per = compatible(list(vlayers), toff, W)
    if not ok:
        raise SystemExit(f"{module}: layers {vlayers} have no common MY track offset")
    tpl, worst = make_template(base, W, H, toff, vlayers)
    stem = out_stem or module
    tf = f"inputs/core_pins/{stem}_tpl.json"
    lf = str(Path(h0["lef"]).with_name(f"{stem}_tpl.lef"))
    dirs = lef_dirs(root / h0["lef"])
    pinhash = hashlib.sha256(json.dumps(tpl, sort_keys=True).encode()).hexdigest()[:12]
    tj = dict(module=module, lef=lf, pinhash=pinhash, pins=tpl,
              source=(f"TYPE-REDUCE-2 pin_template.py: ONE table for every {module} instance (was {len(files)} "
                      f"tables {files}); N/S V pins on {list(vlayers)} only (mirror-compatible), order kept, max shift "
                      f"{worst:.3f} um from {base_f}; MY instances use track offset x + {float(delta):.4f}"))
    for k in ("const_pins_dropped",):
        if k in bj:
            tj[k] = bj[k]
    # rewrite instances
    T = {p["name"]: p for p in tpl}
    disp, changes, stale = [], [], set()
    for k, h in ent:
        _, old = load_pins(pdir, h["pins_file"])
        rel = relation(base, old, W, H)[0] if h["pins_file"] != base_f else "same"
        if rel == "ports-differ" and h["pins_file"].endswith("_xm.json") and \
                {p["name"] for p in old} <= {p["name"] for p in base}:
            rel = "mirror-x"                                # stale _xm view missing ports (S81 vq/vs const_rename bug)
            stale.add(h["pins_file"])
        was_xm = rel == "mirror-x"
        if h["pins_file"] != base_f and not was_xm:
            raise SystemExit(f"{module}: table {h['pins_file']} is not a mirror of {base_f}; not merged")
        o = h.get("orient", "R0")
        no = FLIP_X[o] if was_xm else o
        to = list(h.get("track_offset_um") or [0, 0])
        if was_xm:
            to[0] = round(float(to[0]) + float(delta), 4)
        ox = float(h["origin_um"][0]) + float(to[0])
        for p in old:                                       # parent-frame displacement (x only; y kept by MX)
            q = T.get(p["name"])
            if not q:
                continue
            xo = p["x"] if o in ("R0", "MX") else W - p["x"]
            xn = q["x"] if no in ("R0", "MX") else W - q["x"]
            disp.append(abs((float(h["origin_um"][0]) + float((h.get("track_offset_um") or [0])[0]) + xo) - (ox + xn)))
            if LATTICE[q["layer"]][2] == "V" and face_of(q, W, H) in "NS" and not on_track(q["layer"], ox + xn):
                raise SystemExit(f"{module} in {k}: pin {q['name']} off track after orient {no}")
        changes.append((k, h["inst"], h["pins_file"], o, no, to))
        h.update(pins_file=tf, lef=lf, orient=no, track_offset_um=to)
        h["note"] = (h.get("note", "") + f" | TYPE-REDUCE-2: template table {tf} (orient {o}->{no})").strip(" |")
    disp.sort()
    stats = dict(module=module, tables_before=files, template=tf, instances=len(ent), max_shift_core_um=round(worst, 4),
                 parent_disp_um=dict(max=round(disp[-1], 3) if disp else 0, p90=round(disp[int(0.9 * len(disp))], 3)
                                     if disp else 0), my_track_offset_delta=float(delta), stale_mirror_views=sorted(stale), changes=changes)
    return tj, lf, lef(module, W, H, tpl, dirs), stats


COMPACT = ("hard_cores", "ft_slots", "contents")


def dumps(p, compact=COMPACT):
    """repo plan format (results/s81_faultfeed_1025/fmt.py): indent 1, list entries of these type keys compact"""
    import copy
    p = copy.deepcopy(p)
    keep = []
    for t in p["partition_types"].values():
        for key in compact:
            for i, s in enumerate(t.get(key) or []):
                keep.append(json.dumps(s, separators=(",", ":")))
                t[key][i] = "@@PT%d@@" % (len(keep) - 1)
    txt = json.dumps(p, indent=1)
    return re.sub(r'"@@PT(\d+)@@"', lambda m: keep[int(m.group(1))], txt) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["check", "make"])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--module", action="append")
    ap.add_argument("--vlayers", default="M5")
    ap.add_argument("--write", action="store_true", help="make: write tables, LEFs and the plan in place")
    a = ap.parse_args(argv)
    root, plan_p = Path(a.root), Path(a.plan)
    pdir = plan_p.parent
    plan = json.loads(plan_p.read_text())
    if a.cmd == "check":
        print(json.dumps(check(plan, pdir, root), indent=1))
        return
    allst = []
    for m in a.module or []:
        tj, lf, ltext, st = make(plan, pdir, root, m, tuple(a.vlayers.split(",")))
        allst.append(st)
        if a.write:
            (pdir / st["template"]).write_text(json.dumps(tj, indent=0))
            (root / lf).write_text(ltext)
        print(json.dumps({k: v for k, v in st.items() if k != "changes"}))
    if a.write:
        plan_p.write_text(dumps(plan))
    return allst


if __name__ == "__main__":
    main()
