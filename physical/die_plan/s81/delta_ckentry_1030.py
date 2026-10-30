#!/usr/bin/env python3
"""S81 one-block clock-entry fix (DIE-S81-36/CKENTRY, 2026-10-30; COORD ruling 13:49 path (b)): clk of attn_hcore and
the leaf cores vs / ve_m / vn_a / vn_b = explicit M5 interior centre entry (12.8a face C), ve_s 541266add form.

Why: S81-CORES-KITS-4 13:48 (CHECKED auto_geom): attn_hcore ev3k3 AUTO-GEOM FAIL clock_reach 328 um from its S-edge
clk only; estimated reach from the edge pins vs ~250 / ve_m ~420 / vn_a ~430 / vn_b ~440 um, all > 220.

Entry = master_plan.core_entry() default (core centre on the 4.32-um lattice), snapped onto the M5 track exactly as
master_slice.snap_on_track (x = 0.012 + 0.048 k, ties up) at CLOCK_PIN_SIZE 0.048 x 0.48.  Island = entry +-2.16 um
(ve_s ck_entry island form).  Per core (nothing else changes):
  pins json   clk (old edge xy) -> (new interior xy), source note appended, pinhash recomputed
  plan LEF    clk PORT M5 RECT -> 0.048 x 0.48 at the entry (USE kept);
              leaf tpl LEFs (obs_max M7, full-outline M6/M7 OBS): M6/M7 OBS opened over the island (ve_s form);
              attn_hcore LEF (obs_max M5): the old S-edge M5 OBS notch is closed and the same notch is cut around the
              new pin (M5 OBS covers everything but the pin shape, PINEV 10-29 form)
  plan        early die taps kind core '<inst>.clk' (ve_m 78, vn_a 78, vn_b 74 rows; vs and attn_hcore have none):
              xy += orient(dx, dy), (dx, dy) = new - old pin, keeping each row's per-orient offset from its pin
              (type-internal tap move, VSW 66945faffaf form).  insertion_ps / insertion_ff_ps unchanged until the new
              centre-entry views are signed off.  Rewritten by exact textual xy replacement of those rows only.
usage: python3 delta_ckentry_1030.py PLAN   (asserts exact old forms; a second run refuses)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

S81 = Path(__file__).resolve().parent
PIN_W, PIN_L = 0.048, 0.48
LAT, HALF = 4.32, 2.16
CORES = {
    # module: (pins json, lef, (W, H), old clk xy, old LEF rect text, die-tap name or None, LEF kind)
    "ot_s81sl_vs": ("inputs/core_pins/ot_s81sl_vs_tpl.json", "cores/leaf/lef/ot_s81sl_vs_tpl.lef", (172.8, 172.8),
                    (85.164, 0.24), "85.1400 0.0000 85.1880 0.4800", None, "leaf"),
    "ot_s81sl_ve_m": ("inputs/core_pins/ot_s81sl_ve_m_tpl.json", "cores/leaf/lef/ot_s81sl_ve_m_tpl.lef", (172.8, 345.6),
                      (86.316, 0.24), "86.2920 0.0000 86.3400 0.4800", "u_lf.u_ve.u_m.clk", "leaf"),
    "ot_s81sl_vn_a": ("inputs/core_pins/ot_s81sl_vn_a_tpl.json", "cores/leaf/lef/ot_s81sl_vn_a_tpl.lef", (356.4, 164.16),
                      (0.06, 81.9), "0.0000 81.6600 0.1200 82.1400", "u_lf.u_vn.u_a.clk", "leaf"),
    "ot_s81sl_vn_b": ("inputs/core_pins/ot_s81sl_vn_b_tpl.json", "cores/leaf/lef/ot_s81sl_vn_b_tpl.lef", (356.4, 172.8),
                      (0.06, 86.316), "0.0000 86.0760 0.1200 86.5560", "u_lf.u_vn.u_b.clk", "leaf"),
    "ot_s81c_attn_hcore": ("inputs/core_pins/ot_s81c_attn_hcore.json", "cores/svc/ot_s81c_attn_hcore.lef",
                           (157.68, 259.2), (78.828, 0.24), "78.804 0.000 78.852 0.480", None, "attn"),
}
N_TAPS = {"u_lf.u_ve.u_m.clk": 78, "u_lf.u_vn.u_a.clk": 78, "u_lf.u_vn.u_b.clk": 74}


def snap(v):
    return round(round(v / LAT) * LAT, 4)


def entry(W, H):
    import math
    x, y = snap(W / 2), snap(H / 2)
    x = 0.012 + math.floor((x - 0.012) / 0.048 + 0.5) * 0.048          # M5 vertical: track in x
    return round(x, 4), round(y, 4)


def rect(xy):
    x, y = xy
    return (x - PIN_W / 2, y - PIN_L / 2, x + PIN_W / 2, y + PIN_L / 2)


def island(xy, W, H):
    x, y = xy
    r = (round(x - HALF, 3), round(y - HALF, 3), round(x + HALF, 3), round(y + HALF, 3))
    assert 0 < r[0] and r[2] < W and 0 < r[1] and r[3] < H
    return r


def edit_pins(mod, path, old, new):
    p = S81 / path
    txt = p.read_text()
    o = '"name": "clk",\n"layer": "M5",\n"x": %g,\n"y": %g\n' % old
    assert txt.count(o) == 1, (mod, "clk entry not in the expected form")
    d0 = json.loads(txt)
    txt = txt.replace(o, '"name": "clk",\n"layer": "M5",\n"x": %g,\n"y": %g\n' % new)
    d = json.loads(txt)
    d["source"] += ("; S81 one-block clock-entry fix DIE-S81-36/CKENTRY 2026-10-30 (delta_ckentry_1030.py): clk M5 edge "
                    "(%g,%g) -> M5 interior centre entry (%g,%g) 0.048x0.48 face C" % (old + new))
    d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
    txt = txt.replace(json.dumps(d0["source"])[1:-1], json.dumps(d["source"])[1:-1], 1)
    assert txt.count('"pinhash": "%s"' % d0["pinhash"]) == 1
    txt = txt.replace('"pinhash": "%s"' % d0["pinhash"], '"pinhash": "%s"' % d["pinhash"], 1)
    assert json.loads(txt) == d
    p.write_text(txt)
    return d0["pinhash"], d["pinhash"]


def edit_lef(mod, path, oldrect, new, W, H, kind):
    p = S81 / path
    txt = p.read_text()
    m = re.search(r"(  PIN clk\n    DIRECTION INPUT ;\n    USE \w+ ;\n    PORT\n      LAYER M5 ;\n        RECT )"
                  r"([^;]+?)( ;\n    END\n  END clk\n)", txt)
    assert m and m.group(2) == oldrect and txt.count("  PIN clk\n") == 1, (mod, "clk PORT not in the expected form")
    nd = 4 if kind == "leaf" else 3
    x0, y0, x1, y1 = rect(new)
    txt = txt[:m.start(2)] + f"{x0:.{nd}f} {y0:.{nd}f} {x1:.{nd}f} {y1:.{nd}f}" + txt[m.end(2):]
    a, b, c, e = island(new, W, H)
    assert a < x0 and x1 < c and b < y0 and y1 < e
    if kind == "leaf":
        for lay in ("M6", "M7"):
            o = f"    LAYER {lay} ;\n      RECT 0 0 {W:.3f} {H:.3f} ;\n"
            assert txt.count(o) == 1, (mod, lay, "OBS not in the expected full-outline form")
            n = (f"    LAYER {lay} ;\n      RECT 0 0 {W:.3f} {b:.3f} ;\n      RECT 0 {e:.3f} {W:.3f} {H:.3f} ;\n"
                 f"      RECT 0 {b:.3f} {a:.3f} {e:.3f} ;\n      RECT {c:.3f} {b:.3f} {W:.3f} {e:.3f} ;\n")
            txt = txt.replace(o, n)
    else:
        o = ("    LAYER M5 ;\n      RECT 0.200 0.200 78.780 259.000 ;\n      RECT 78.876 0.200 157.480 259.000 ;\n"
             "      RECT 78.780 0.504 78.876 259.000 ;\n  END\n")
        assert txt.count(o) == 1, (mod, "M5 OBS notch not in the expected form")
        assert not re.search(r"^\s*LAYER M[6-9] ;", txt.split("\n  OBS\n", 1)[1], re.M)
        n = (f"    LAYER M5 ;\n      RECT 0.200 0.200 {x0:.3f} 259.000 ;\n      RECT {x1:.3f} 0.200 157.480 259.000 ;\n"
             f"      RECT {x0:.3f} 0.200 {x1:.3f} {y0:.3f} ;\n      RECT {x0:.3f} {y1:.3f} {x1:.3f} 259.000 ;\n  END\n")
        txt = txt.replace(o, n)
    p.write_text(txt)


def fmt(v):
    return repr(round(v, 3))


def edit_plan(plan, moves_by_tap):
    """moves_by_tap {tap name: (module, old, new, W, H)}"""
    txt = plan.read_text()
    p = json.loads(txt)
    out = {}
    for tap, (mod, old, new, W, H) in moves_by_tap.items():
        dx, dy = new[0] - old[0], new[1] - old[1]
        inst = tap[:-len(".clk")]
        rows = {}
        for tn, t in p["partition_types"].items():
            hc = {h["inst"]: h for h in t.get("hard_cores", []) or [] if h["module"] == mod}
            for tp in (t.get("clock") or {}).get("taps", []) or []:
                if tp.get("name") != tap:
                    continue
                assert tp.get("kind") == "core", (tn, tp.get("kind"))
                h = hc[inst]
                o = h["orient"]
                ox, oy = h["origin_um"]
                sx = -1 if o in ("MY", "R180") else 1
                sy = -1 if o in ("MX", "R180") else 1
                px = ox + (old[0] if sx > 0 else W - old[0])
                py = oy + (old[1] if sy > 0 else H - old[1])
                assert abs(tp["xy"][0] - px) < 0.2 and abs(tp["xy"][1] - py) < 0.3, (tn, tp["xy"], px, py)
                nx, ny = round(tp["xy"][0] + sx * dx, 3), round(tp["xy"][1] + sy * dy, 3)
                assert ox < nx < ox + W and oy < ny < oy + H, (tn, nx, ny)
                rows[tn] = (tuple(tp["xy"]), (nx, ny))
                tp["xy"] = [nx, ny]
        assert len(rows) == N_TAPS[tap], (tap, len(rows))
        pat = re.compile(r'("name": "%s",\s*"kind": "core",\s*"xy": \[\s*)([-0-9.]+)(,\s*)([-0-9.]+)(\s*\])'
                         % re.escape(tap))
        assert len(pat.findall(txt)) == N_TAPS[tap], (tap, "textual tap rows", len(pat.findall(txt)))
        new_of = {}
        for o_, n_ in rows.values():
            new_of.setdefault((round(o_[0], 3), round(o_[1], 3)), set()).add(n_)

        def sub(m):
            (n,) = new_of[(round(float(m.group(2)), 3), round(float(m.group(4)), 3))]
            return f"{m.group(1)}{fmt(n[0])}{m.group(3)}{fmt(n[1])}{m.group(5)}"
        txt = pat.sub(sub, txt)
        out[tap] = len(rows)
    assert json.loads(txt) == p, "textual edit != structural edit"
    plan.write_text(txt)
    return out


if __name__ == "__main__":
    plan = Path(sys.argv[1]).resolve()
    taps = {}
    for mod, (pins, lef, (W, H), old, oldrect, tap, kind) in CORES.items():
        new = entry(W, H)
        h = edit_pins(mod, pins, old, new)
        edit_lef(mod, lef, oldrect, new, W, H, kind)
        if tap:
            taps[tap] = (mod, old, new, W, H)
        print(mod, "clk", old, "->", new, "rect", tuple(round(v, 4) for v in rect(new)), "island", island(new, W, H),
              "pinhash", h)
    print("taps moved", edit_plan(plan, taps))
