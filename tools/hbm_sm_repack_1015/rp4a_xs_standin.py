#!/usr/bin/env python3
"""L2H-SMATT/RP4A (10-19): DIAGNOSTIC-ONLY stand-in abstract of the NOT-YET-CLOSED x store smh_xs_ring_p192c_1019
(ot_hbm_accel_smh_xs, 475.2 x 302.4, gate WARN clean, in COORD review) for the rp4a attention-tile parent gates.
NEVER bindable, never submitted: the view directory carries STANDIN_NOT_A_VIEW and PROVISIONAL_NOT_A_VIEW, and the kit
dir is named *_standin.

Geometry: the p192c footprint (475.2 x 302.4) and its pin FACES (spec "pins": N = clk / rst / straps / o_iv_b / o_ifirst /
o_ilast / o_ifp4 / o_itag / o_iw / o_ix, S = bk1, E = o_*_e / o_iv_f, W = rl1 / ohl1); each face's pins spread evenly over
the face (4.32 um end margins) in spec port order on the asap7 track grid (N/S M5, W/E M4; >= 4 tracks apart = p192c
pin_min_tracks 4).  PG: M6 VDD / VSS stripes at the closed xs pitch (10.8, 2.16 inset).  OBS: M1-M5 over the body minus
10.8-um pin-access windows on M4-M5 at every face pin cluster (tools/abstract_pin_windows.py); M6+ free (p192c caps M6).
Timing: the CLOSED smh_xs_ref_p45m ETM libs (same ports, same RTL cycles: p192c adds 0 edges) with the cell area set to
the p192c footprint.  KNOWN UNDER-STATEMENT: p45m TT boundary insertion 315 ps vs p192c measured ~618 ps (gate TT), so the
parent's hard-child clock reference sees ~300 ps less xs insertion than the final view; the parent gate's clock numbers
are diagnostic until the closed p192c view replaces this stand-in.
    python3 tools/hbm_sm_repack_1015/rp4a_xs_standin.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import abstract_pin_windows as APW  # noqa: E402

SRC = ROOT / "physical/ref_tile/smh_xs_ref_p45m/views/ot_hbm_accel_smh_xs"
SPEC = ROOT / "physical/ref_tile/smh_xs_ring_p192c_1019/spec.json"
OUT = ROOT / "physical/ref_tile/smh_xs_p192c_standin/views/ot_hbm_accel_smh_xs"
NAME = "ot_hbm_accel_smh_xs"
TRACK = {"M4": (0.012, 0.048), "M5": (0.012, 0.048)}
MARGIN, MINSEP = 4.32, 0.192


def src_pins():
    t = (SRC / f"{NAME}.lef").read_text()
    out = []
    for m in re.finditer(r"\n  PIN (\S+)\n(.*?)\n  END \1", t, re.S):
        nm, body = m.group(1), m.group(2)
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        d = re.search(r"DIRECTION (\w+)", body).group(1)
        u = re.search(r"USE (\w+)", body).group(1)
        b = re.match(r"(\w+)(?:\[(\d+)\])?$", nm)
        out.append((nm, b.group(1), int(b.group(2) or 0), d, u))
    return out


def place(W, H, pins, faces):
    order = {}
    for f, names in faces.items():
        for k, n in enumerate(names):
            order[n] = (f, k)
    by = {}
    for p in pins:
        if p[1] not in order:
            raise SystemExit(f"port {p[1]} has no p192c face")
        f, k = order[p[1]]
        by.setdefault(f, []).append((k, p[2], p))
    placed = []
    for f, lst in sorted(by.items()):
        lst.sort()
        L = W if f in "NS" else H
        lay = "M5" if f in "NS" else "M4"
        off, pit = TRACK[lay]
        n = len(lst)
        span = L - 2 * MARGIN
        if span / n < MINSEP:
            raise SystemExit(f"face {f}: {n} pins over {span:.1f} um < {MINSEP} um apart")
        last = -1e9
        for i, (_k, _b, p) in enumerate(lst):
            pos = MARGIN + span * (i + 0.5) / n
            pos = off + round((pos - off) / pit) * pit
            if pos - last < MINSEP - 1e-6:
                pos = off + round((last + MINSEP - off) / pit + 0.4999) * pit
            last = pos
            if f in "SN":
                y0, y1 = (0.0, 0.084) if f == "S" else (H - 0.084, H)
                r = (pos - 0.012, y0, pos + 0.012, y1)
            else:
                x0, x1 = (0.0, 0.084) if f == "W" else (W - 0.084, W)
                r = (x0, pos - 0.012, x1, pos + 0.012)
            placed.append((p, f, lay, r))
    return placed


def lef(W, H, placed):
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "UNITS", "    DATABASE MICRONS 1000 ;", "END UNITS", "",
         f"MACRO {NAME}", f"  FOREIGN {NAME} 0 0 ;", "  CLASS BLOCK ;", f"  SIZE {W} BY {H} ;"]
    pinrects = []
    for (nm, _b, _i, d, u), _f, lay, r in placed:
        pinrects.append((nm, lay, r))
        L += [f"  PIN {nm}", f"    DIRECTION {d} ;", f"    USE {u} ;", "    PORT", f"      LAYER {lay} ;",
              "        RECT  %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {nm}"]
    for net, use, y0 in (("VDD", "POWER", 4.4), ("VSS", "GROUND", 4.016)):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M6 ;"]
        y = y0
        while y + 0.288 < H - 2.16:
            L.append("        RECT  2.16 %.3f %.3f %.3f ;" % (y, W - 2.16, y + 0.288))
            y += 10.8
        L += ["    END", f"  END {net}"]
    win = APW.windows(W, H, pinrects, 10.8, 4, 5)
    L += ["  OBS"]
    for k in range(1, 6):
        L += [f"    LAYER M{k} ;"] + ["      RECT  %.3f %.3f %.3f %.3f ;" % q
                                     for q in APW.minus_rect((0.06, 0.06, W - 0.06, H - 0.06), win.get(k, []))]
    L += ["  END", f"END {NAME}", "", "END LIBRARY"]
    return "\n".join(L) + "\n"


def main():
    sp = json.loads(SPEC.read_text())
    W, H = sp["outline"]["w"], sp["outline"]["h"]
    pins = src_pins()
    placed = place(W, H, pins, sp["pins"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.lef").write_text(lef(W, H, placed))
    for c in ("tt", "ff", "ss"):
        t = (SRC / f"{NAME}_{c}.lib").read_text()
        t, n = re.subn(r"(\n\s*area\s*:\s*)[\d.]+", lambda m: m.group(1) + f"{W * H:.4f}", t, count=1)
        (OUT / f"{NAME}_{c}.lib").write_text(t)
    (OUT / "insertion.json").write_text((SRC / "insertion.json").read_text())
    note = ("diagnostic stand-in of smh_xs_ring_p192c_1019 (not closed): p192c footprint + pin faces, closed p45m ETM "
            "timing (insertion under-stated ~300 ps TT); never bind, never submit\n")
    (OUT / "STANDIN_NOT_A_VIEW").write_text(note)
    (OUT / "PROVISIONAL_NOT_A_VIEW").write_text("standin\n")
    cnt = {}
    for _p, f, lay, _r in placed:
        cnt[f] = cnt.get(f, 0) + 1
    print(f"{OUT}: {W} x {H}, pins per face {cnt}")


if __name__ == "__main__":
    main()
