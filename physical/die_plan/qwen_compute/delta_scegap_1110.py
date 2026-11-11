#!/usr/bin/env python3
"""DIE-QC-97 SC-EGAP 11-10 plan event: take the ft station rises out of the east gap of the QC sc types.

MEASURED cause (failed kits' GRT congestion reports): sle_sc_v1__cl115da35f route FAIL GRT-0116, 16179 overflow
(M6 11126), every entry at x 518-612 / y 648-864.  That is the south-east corner of the qfd_dv_s5_sc2_leaf* hard core
(x 345.6-590.16, y 648-1162.08) and the 23.28 um gap between it and the E outline.  In the sle sc types the last
station of several W -> E ft slots sits below (or above) the core, so their 260-550 bits must run vertically up the
gap to their E-face window, beside the 456-bit x_su_l1_ctl column at x 604.8.  The slw types put those stations
west of the core at the window height (x 342), so the bits cross the core straight on M6; they route (slw_sc_v3:
64 overflow, max 1).  Its residue is x_fe_stm_p1 (E -> W): it enters at y 999-1102 and climbs the gap to its first
station (362.9, 1175.0) above the core.

Form (the slw layout; station count, bit order and every port unchanged, so no latency / pin / RTL change): move each
listed station's register point and its bit-site group rigidly to TARGET (x ~318 at the E-window mid y for a W -> E
last station; (342, 1100) for slw_sc_v3 x_fe_stm_p1 st0).  The move is snapped to the site grid (x 0.216 um, y
0.27 um rows), then legalised by the nearest clear offset (2.16 um steps): no moved site box may overlap another
slot's site, another station of the same slot, a count-strap site, a landing band rect or a hard core, or leave
the outline.  Per register and per bit, the hops into and out of the moved station must stay <= KNEE_UM (403,
istation knee / ft_knee_sites pitch; the bind reach is 405).
Only partition_types[t].ft_slots[s].regs_um[i] and bit_sites_um[i - 1][*] of the listed stations change.

Refuses: a missing type / slot, a station not at its recorded position (already applied, or the plan changed: merge
by hand), an E window that no longer overlaps the core rows, and any move that cannot be legalised or breaks a hop.
    delta_scegap_1110.py PLAN.json OUT.json   -> prints {moves, sha256_in, sha256_out}
"""
import argparse
import hashlib
import json
from pathlib import Path

KNEE_UM = 403.0
X_TARGET = 318.0
SITE_X, SITE_Y = 0.216, 0.27
STEP = 2.16                        # legalisation step (10 site columns / 8 rows)
MAX_STEPS = 24                     # +-51.8 um search

_W2E_CL115 = (("x_fw_fe_p1", 2, (475.2, 596.16)), ("x_fw_fe_p2", 3, (544.32, 639.36)),
              ("x_fw_st_b", 3, (604.8, 648.0)), ("x_stm_fe", 3, (466.56, 1175.04)))
# (slot, regs_um index of the moved station, its current register point, target or None = (X_TARGET, window mid))
MOVES = {
    "sle_sc_v1__cl115da35f": tuple(m + (None,) for m in _W2E_CL115),
    "sle_sc_v1__cl7479a5ec": tuple(m + (None,) for m in _W2E_CL115),
    "sle_sc_v2": (("x_fw_fe_p1", 2, (501.12, 622.08), None), ("x_fw_fe_p2", 3, (604.8, 630.72), None),
                  ("x_stm_fe", 3, (449.28, 1175.04), None)),
    "sle_sc_v3": (("x_fw_fe", 2, (457.92, 518.4), None), ("x_fw_fe_p1", 2, (466.56, 622.08), None),
                  ("x_fw_fe_p2", 3, (604.8, 639.36), None), ("x_stm_fe_p1", 2, (457.92, 1175.04), None)),
    "slw_sc_v3": (("x_fe_stm_p1", 1, (362.88, 1175.04), (342.0, 1100.0)),),
}


def r4(v):
    return round(v + 0.0, 4)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _slot(t, name):
    for f in t.get("ft_slots") or []:
        if f.get("name") == name:
            return f
    return None


def _close(a, b):
    return abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3


def _box(p, cell):
    return (p[0], p[1], p[0] + cell[0], p[1] + cell[1])


def _ov(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _face_pt(f, p, W, H, side):
    """the face point a bit at p connects to: side 'out' = out face / out window, 'in' = in face (clamped)."""
    face = f["out_face"] if side == "out" else f["in_face"]
    win = f.get("out_window_um") if side == "out" else f.get("in_window_um")
    lo, hi = (win or (0.0, H if face in "EW" else W))[:2]
    if face in "EW":
        return (W if face == "E" else 0.0, min(max(p[1], lo), hi))
    return (min(max(p[0], lo), hi), H if face == "N" else 0.0)


def _neighbours(f, i, W, H):
    """per-bit neighbour points before / after station i (regs index), and the register-level ones."""
    regs = [tuple(r) for r in f["regs_um"]]
    S = f["bit_sites_um"]
    k = i - 1
    prev_bits = S[k - 1] if k >= 1 else None
    nxt_bits = S[k + 1] if k + 1 < len(S) else None
    prev_reg = regs[i - 1]
    nxt_reg = regs[i + 1] if i + 1 < len(regs) else _face_pt(f, regs[i], W, H, "out")
    return prev_bits, nxt_bits, prev_reg, nxt_reg, regs[0]


def _hops(f, i, grp, reg, W, H):
    prev_bits, nxt_bits, prev_reg, nxt_reg, entry = _neighbours(f, i, W, H)
    hr = max(man(prev_reg, reg), man(reg, nxt_reg if i + 1 < len(f["regs_um"]) else _face_pt(f, reg, W, H, "out")))
    hb = 0.0
    for j, p in enumerate(grp):
        a = prev_bits[j] if prev_bits and j < len(prev_bits) else entry
        b = nxt_bits[j] if nxt_bits and j < len(nxt_bits) else _face_pt(f, p, W, H, "out")
        hb = max(hb, man(a, p), man(p, b))
    return hr, hb


def _obstacles(t, f, k, cell):
    obs = []
    for g in t.get("ft_slots") or []:
        gc = g.get("bit_site_cell_um") or cell
        for gi, grp in enumerate(g.get("bit_sites_um") or []):
            if g is f and gi == k:
                continue
            if grp and isinstance(grp[0], list):
                obs += [_box(p, gc) for p in grp]
    for s in t.get("count_straps") or []:
        obs += [_box(p, cell) for p in (s.get("sites_um") or []) if isinstance(p, list)]
    for b in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).values():
        if b.get("rect_um"):
            obs.append(tuple(map(float, b["rect_um"])))
    for h in t.get("hard_cores") or []:
        (ox, oy), (cw, ch) = h["origin_um"], h["outline_um"]
        obs.append((ox, oy, ox + cw, oy + ch))
    return obs


def _snap(v, q):
    return round(round(v / q) * q, 4)


def move_station(tn, t, slot, i, orig, target):
    f = _slot(t, slot)
    if f is None:
        raise SystemExit(f"SCEGAP: {tn} has no ft slot {slot}")
    if not _close(f["regs_um"][i], orig):
        raise SystemExit(f"SCEGAP: {tn} {slot} station {i - 1} at {f['regs_um'][i]}, expected {list(orig)} "
                         "(event already applied or plan changed: merge by hand)")
    W, H = map(float, t["outline_um"])
    core = [(h["origin_um"][1], h["origin_um"][1] + h["outline_um"][1]) for h in t.get("hard_cores") or []]
    if target is None:
        if f.get("out_face") != "E":
            raise SystemExit(f"SCEGAP: {tn} {slot} is not a W -> E slot")
        lo, hi = f["out_window_um"]
        if not any(lo < c1 and c0 < hi for c0, c1 in core):
            raise SystemExit(f"SCEGAP: {tn} {slot} E window {lo}-{hi} no longer beside the core rows")
        target = (X_TARGET, (lo + hi) / 2)
    k = i - 1
    grp0 = [list(p) for p in f["bit_sites_um"][k]]
    cell = f.get("bit_site_cell_um") or [1.404, 0.27]
    dx0 = _snap(target[0] - orig[0], SITE_X)
    dy0 = _snap(target[1] - orig[1], SITE_Y)
    obs = _obstacles(t, f, k, cell)
    cands = sorted(((a, b) for a in range(-MAX_STEPS, MAX_STEPS + 1) for b in range(-MAX_STEPS, MAX_STEPS + 1)),
                   key=lambda ab: (abs(ab[0]) + abs(ab[1]), abs(ab[1]), ab))
    for a, b in cands:
        dx, dy = r4(dx0 + a * STEP), r4(dy0 + b * STEP)
        grp = [[r4(p[0] + dx), r4(p[1] + dy)] for p in grp0]
        reg = [r4(orig[0] + dx), r4(orig[1] + dy)]
        if min(p[0] for p in grp) < 0 or max(p[0] for p in grp) + cell[0] > W or \
                min(p[1] for p in grp) < 0 or max(p[1] for p in grp) + cell[1] > H:
            continue
        boxes = [_box(p, cell) for p in grp]
        if any(_ov(bx, o) for bx in boxes for o in obs):
            continue
        hr, hb = _hops(f, i, grp, reg, W, H)
        if hr > KNEE_UM or hb > KNEE_UM:
            continue
        hr0, hb0 = _hops(f, i, grp0, list(orig), W, H)
        f["regs_um"][i] = reg
        f["bit_sites_um"][k] = grp
        return dict(type=tn, slot=slot, station=k, frm=list(orig), to=reg, nudge_um=[r4(a * STEP), r4(b * STEP)],
                    reg_hop_max=[round(hr0, 2), round(hr, 2)], bit_hop_max=[round(hb0, 2), round(hb, 2)],
                    sites=len(grp))
    raise SystemExit(f"SCEGAP: {tn} {slot} station {k}: no legal site group within +-{MAX_STEPS * STEP} um of "
                     f"{target} (hop <= {KNEE_UM})")


def apply(raw):
    pt = raw["partition_types"]
    missing = [t for t in MOVES if t not in pt]
    if missing:
        raise SystemExit(f"SCEGAP: plan lacks sc types {missing}")
    for tn, mv in MOVES.items():            # refuse before touching anything
        for slot, i, orig, _ in mv:
            f = _slot(pt[tn], slot)
            if f is None:
                raise SystemExit(f"SCEGAP: {tn} has no ft slot {slot}")
            if not _close(f["regs_um"][i], orig):
                raise SystemExit(f"SCEGAP: {tn} {slot} station {i - 1} at {f['regs_um'][i]}, expected {list(orig)} "
                                 "(event already applied or plan changed: merge by hand)")
    rep = []
    for tn, mv in MOVES.items():
        for slot, i, orig, target in mv:
            rep.append(move_station(tn, pt[tn], slot, i, orig, target))
    return raw, rep


def _style(b, obj):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, separators=(",", ":"))):
        if f(obj).encode() == b:
            return f
    raise SystemExit("SCEGAP: input JSON style not recognised (would not stay byte-same)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    raw = json.loads(src)
    dump = _style(src, raw)
    raw, rep = apply(raw)
    out = dump(raw).encode()
    Path(a.output).write_bytes(out)
    print(json.dumps({"moves": rep, "sha256_in": hashlib.sha256(src).hexdigest(),
                      "sha256_out": hashlib.sha256(out).hexdigest()}))


if __name__ == "__main__":
    main()
