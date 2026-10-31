#!/usr/bin/env python3
"""S81-SERDES-PHY-3 10-31: one metadata event: place the two KP4 decoder SRAM leaves of every PMA-placed serdes type.

The serdes kits (PMA views, delta_pma_views_1031) reach two more hard leaves inside u_phy's bound netlist:
u_core.u_dec.u_dly.u_dmem (ot_sram_1r1w2c_64x546_m1, 178.632 x 81) and u_core.u_dec.u_out.u_cmem (ot_sram_1r1w_32x546_m1,
177.768 x 81).  Without a placement the kit stops at synth_odb (ORD-2013 LEF master not found; serdes__t16 pilot 10-31).
They are core-VDD macros, so they sit OUTSIDE the PHY PG domain / clock keepout, in the digital part of the type:
side by side (gap 10.8 = the kit_preflight macro channel), centred under the rx PMA, at the top of the highest free
horizontal band below the shore keepout (free = not a clock keepout, not an ft_slot pin window band, >= 10.8 off both,
no grid tap within the 8.64 tap clearance); a type whose whole digital band is ft pin windows (serdes t1 x2, t3) takes the
highest keepout-free site inside an ft band instead, each SRAM in its own gap between the default station columns
(receipt in_ft_band; the ft bits run on M6 over the M1-M4 SRAM OBS, no station site inside a macro).  Added as physical_parts of u_phy (they are leaves of ot_pdie_serdes); the type gets core_pg_connect: true
and type-level PHY pads for the PMA line side (io_pma_tx/tck/rx/rck, HEAD-BIND-4 form; port_bind counted them as extra)
(G0C core_pg: the kit PDN must land vias on the SRAM PG pins).
Types without PMA parts are untouched.  Refuses a second run.

    python3 physical/die_plan/s81/delta_kp4_srams_1031.py PLAN_IN PLAN_OUT RECEIPT
"""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S  # noqa: E402

VIEWS = "physical/asap7_memory_macros"
H = 81.0
LEAVES = (("u_bound.u_core.u_dec.u_dly.u_dmem", "ot_sram_1r1w2c_64x546_m1", 178.632),
          ("u_bound.u_core.u_dec.u_out.u_cmem", "ot_sram_1r1w_32x546_m1", 177.768))
GAP = 10.8
X_GRID, Y_GRID, Y_OFF = 0.864, 1.08, 0.012        # the S81 plan SRAM site convention (x k*0.864, y k*1.08 + 0.012)
CLEAR = S.TAP_CLEAR_UM
# the PMA line side of the bound serdes wrapper (kit-rtl bound-only pins io_pma_*): type-level PHY pads (HEAD-BIND-4
# form, as hd_serdes): exact kit ports with no boundary flop, PHY clocks flagged
PADS = (dict(name="io_pma_tx", dir="out", width=544), dict(name="io_pma_tck", dir="out", width=1, clock=True),
        dict(name="io_pma_rx", dir="in", width=544), dict(name="io_pma_rck", dir="in", width=1, clock=True))


def part(inst, master, w, x, y):
    return {"physical_inst": inst, "physical_master": master, "lef": f"{VIEWS}/{master}/{master}.lef",
            "lib": f"{VIEWS}/{master}/{master}_tt.lib", "origin_um": [x, y], "outline_um": [w, H], "orient": "R0"}


def place(t, taps, ft_bands=True):
    """[(inst, master, w, x, y)] or None.  ft_bands=False: only the clock keepout blocks (fallback for a type whose
    digital band below the shore is all ft pin windows: the ft bits run on M6 over the M1-M4 SRAM obstruction)."""
    W, Ht = t["outline_um"]
    ko = t.get("clock", {}).get("keepouts_um", []) or []
    blocked = [(k[1], k[3]) for k in ko]
    for s in (t.get("ft_slots", []) or []) if ft_bands else []:
        for key in ("in_window_um", "out_window_um"):
            if s.get(key):
                blocked.append(tuple(s[key]))
    top = min([k[1] for k in ko] or [Ht])                      # shore keepout bottom edge
    edges = sorted({0.0, top} | {b for a, b in blocked if b <= top} | {a for a, b in blocked if a <= top})
    rx = next(q for c in t["contents"] for q in c.get("physical_parts", []) if q["physical_master"] == "ot_s81_pma_rxm")
    xc = rx["origin_um"][0] + rx["outline_um"][0] / 2
    span = sum(w for _, _, w in LEAVES) + GAP
    # free bands below the keepout, highest first
    for y_hi in sorted(edges, reverse=True):
        if y_hi <= 0:
            continue
        lo_edges = [e for e in edges if e < y_hi]
        y_lo = max(lo_edges) if lo_edges else 0.0
        if any(a < y_hi and b > y_lo for a, b in blocked):    # the band itself is a blocked window
            continue
        y_min = y_lo + (GAP if y_lo > 0 else CLEAR)
        y_top = math.floor((y_hi - GAP - H - Y_OFF) / Y_GRID) * Y_GRID + Y_OFF
        for j in range(0, 1000):                               # highest site first, one row per step
            y = y_top - j * Y_GRID
            if y < y_min:
                break
            got = _row(y, xc, span, W, taps) if ft_bands else _row_split(y, xc, W, taps, _station_columns(t, y))
            if got:
                return got
    return None


def _row(y, xc, span, W, taps):
    """the pair at row y, nearest to xc first, no grid tap within the tap clearance of either box (or None)"""
    for k in range(0, 400):
        for sgn in ((1,) if k == 0 else (-1, 1)):
            x0 = math.floor((xc - span / 2 + sgn * k * X_GRID) / X_GRID) * X_GRID
            if x0 < CLEAR or x0 + span > W - CLEAR:
                continue
            out, x = [], x0
            for inst, m, w in LEAVES:
                out.append((inst, m, w, round(x, 3), round(y, 3)))
                x = math.ceil((x + w + GAP) / X_GRID) * X_GRID
            if any(ox - CLEAR < tx < ox + w + CLEAR and oy - CLEAR < ty < oy + H + CLEAR
                   for (_, _, w, ox, oy) in out for (tx, ty) in taps):
                continue
            return out
    return None


def _station_columns(t, y):
    """x of the default (no bit_sites / regs) ft station sites of every straight E-W slot whose window meets the SRAM rows
    [y - CLEAR, y + H + CLEAR]: stage j of n sits at length j/n of the face-to-face route (check.check_ft_macro_sites)"""
    W = t["outline_um"][0]
    xs = set()
    for s in t.get("ft_slots", []) or []:
        lo, hi = s["in_window_um"]
        if hi < y - CLEAR or lo > y + H + CLEAR:
            continue
        if s.get("bit_sites_um") or s.get("regs_um") or {s["in_face"], s["out_face"]} != {"E", "W"}:
            return None                                       # explicit sites / turning slot: no fallback here
        n = int(s.get("stations", 1))
        xs |= {1.0 + (W - 2.0) * j / n for j in range(n + 1)}
    return sorted(xs)


def _row_split(y, xc, W, taps, cols):
    """fallback inside ft bands: each SRAM centred in its own station-column gap, the two gaps nearest xc"""
    if cols is None:
        return None
    cols = sorted(set([0.0, W] + cols))
    gaps = sorted(((a + CLEAR, b - CLEAR) for a, b in zip(cols, cols[1:])), key=lambda g: abs((g[0] + g[1]) / 2 - xc))
    out, used = [], set()
    for inst, m, w in sorted(LEAVES, key=lambda l: -l[2]):
        for g in gaps:
            if g in used or g[1] - g[0] < w:
                continue
            x = round(math.floor(((g[0] + g[1]) / 2 - w / 2) / X_GRID) * X_GRID, 3)
            if x < g[0] or x + w > g[1]:
                x = round(math.ceil(g[0] / X_GRID) * X_GRID, 3)
            if x + w > g[1] or any(x - CLEAR < tx < x + w + CLEAR and y - CLEAR < ty < y + H + CLEAR for tx, ty in taps):
                continue
            out.append((inst, m, w, x, round(y, 3)))
            used.add(g)
            break
        else:
            return None
    return sorted(out, key=lambda o: [l[0] for l in LEAVES].index(o[0]))


def main(src, dst, receipt):
    text = Path(src).read_text()
    plan = json.loads(text)
    P = S.Plan(json.loads(text), src)
    rows, edits, new_pads = [], [], {}
    for tn, t in sorted(plan["partition_types"].items()):
        for c in t.get("contents", []):
            if c.get("module") != "ot_pdie_serdes" or not c.get("physical_parts"):
                continue
            if any(q["physical_master"] == LEAVES[0][1] for q in c["physical_parts"]):
                raise SystemExit(f"{tn}: decoder SRAM parts already present (second run refused)")
            orig = json.loads(json.dumps(c))
            taps = [(x, y) for _, x, y in S.tap_grid(P, tn)]
            got, in_ft = place(t, taps), False
            if got is None:
                got, in_ft = place(t, taps, ft_bands=False), True
            if got is None:
                rows.append(dict(type=tn, placed=False))
                continue
            c["physical_parts"] += [part(*g) for g in got]
            t["core_pg_connect"] = True       # PG-CORECONN: the kit PDN lands VDD/VSS vias on the SRAM PG pins
            if t.get("pads"):
                raise SystemExit(f"{tn}: type pads already present (second run refused)")
            t["pads"] = [dict(p) for p in PADS]
            new_pads[tn] = t["pads"]
            c["note"] = c.get("note", "") + ("; S81-SERDES-PHY-3 10-31: + KP4 decoder SRAM leaves u_dmem/u_cmem (core VDD, "
                                             "below the shore keepout, delta_kp4_srams_1031)")
            edits.append((tn, orig, c))
            rows.append(dict(type=tn, placed=True, in_ft_band=in_ft, sites=[[g[1], g[3], g[4]] for g in got]))
    lines = text.split("\n")
    keys = {ln[3:ln.index('"', 3)]: i for i, ln in enumerate(lines)
            if ln.startswith('  "') and not ln.startswith('   ') and ln.endswith('": {')}
    starts = sorted(keys.values())
    for (tn, old, new) in edits:
        i0 = keys[tn]
        i1 = next((i for i in starts if i > i0), len(lines))
        line = "    " + json.dumps(old, separators=(",", ":"))
        hit = [i for i in range(i0, i1) if lines[i].rstrip(",") == line]
        if len(hit) != 1:
            raise SystemExit(f"{tn}: u_phy record is not one compact line in its type block ({len(hit)})")
        k = hit[0]
        lines[k] = "    " + json.dumps(new, separators=(",", ":")) + ("," if lines[k].endswith(",") else "")
        if not any(ln.strip().rstrip(",") == '"core_pg_connect": true' for ln in lines[i0:i1]):
            assert lines[i0 + 1].startswith('   "module": ') and lines[i0 + 1].endswith(","), tn
            lines.insert(i0 + 2, '   "core_pg_connect": true,')
            lines.insert(i0 + 3, '   "pads": ' + json.dumps(new_pads[tn], separators=(",", ":")) + ',')
            keys = {n: (i + 2 if i > i0 else i) for n, i in keys.items()}
            starts = sorted(keys.values())
    out = "\n".join(lines)
    if json.loads(out) != plan:
        raise SystemExit("textual rewrite does not equal the edited plan")
    Path(dst).write_text(out)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]
    Path(receipt).write_text(json.dumps(dict(kind="S81_KP4_SRAMS_1031", plan_in=sha(text), plan_out=sha(out), rows=rows,
                                             unchanged="outlines, pins, buses, clock, PG domains, cycles, PMA parts"),
                                        indent=1) + "\n")
    print(json.dumps(dict(plan_in=sha(text), plan_out=sha(out), rows=rows)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
