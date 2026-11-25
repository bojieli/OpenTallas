#!/usr/bin/env python3
"""adv_fpconv2.py -- FP-CONVERGE-S81 11-25 (COORD, from FABLE-RC-S81 07:06): five report-only launch / plan checks.

RANK-PILE-PINFACE  (plan, ADV)  >= PILE_BITS station / ft register bits seated inside one 60 x 20 um window (either orientation)
                   within FACE_UM of a hard-core face: S81 col_h9_r2 DRT patch, 85 % of the marks in 60 x 20 um at a macro pin face.
FT-SITE-LEGAL      (plan, ADV + launch gate)  ft_slots register / bit-site xy outside the outline, inside a hard core, or two registers
                   of one slot on the same point: 5 leaf GP aborts on illegal ft sites.  legal_gate(raw, types) -> [lines] for the
                   kit launch preflight (report-only until a caller treats a line as a refusal).
PLACED-REACH       (kit, route goal)  placed_scan.json bits_over_cycle > 0 (or bits_over_reach > OVER_REACH_MAX when given) stops a
                   ROUTE-GOAL kit.  placed_reach(scan_path) -> (stop, line).  Report-only: the line starts WARN; a caller stops the
                   kit only when OT_PLACED_REACH_STOP=1 (placed_reach_decision()).  slice C 3064-8763 bits over a cycle.
LAUNCH-SCOPE       (kit launch)  launch_scope(kit) -> [lines]: bound plan sha != wave plan sha, type outside the event's touched set,
                   or goal 'route' for a type that is signed / has an open functional row / is not FP-clean.
ROW-LEDGER         (plan vs ledger)  row_ledger(applied_rows, ledger_rows) -> [lines]: an applied row/ops file with no ledger line
                   (sha256 + owner + types + PRE verdict), or a ledger line with a different sha.
All WARN lines, never a gate by themselves."""
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as F  # noqa: E402
import adv_geom_static as G  # noqa: E402

PILE_BITS = 2000
WIN_A, WIN_B = 60.0, 20.0
FACE_UM = 25.0
OVER_REACH_MAX = None
MAX_EX = 3


def _w(check, *parts):
    return f"WARN ADV-{check} " + " ".join(str(p) for p in parts)


def _bits_points(t):
    """[(x, y, bits)] station register seats and ft register seats of a type"""
    out = []
    for s in t.get("internal_stations") or []:
        if isinstance(s, dict):
            b = s.get("bits") or 1
            out += [(x, y, b) for x, y in F.pts(s.get("regs_um"))]
    for s in t.get("ft_slots") or []:
        if isinstance(s, dict):
            b = s.get("width") or s.get("bits") or 1
            out += [(x, y, b) for x, y in F.pts(s.get("regs_um"))]
    return out


def rank_pile(t):
    rects = G.hard_rects(t)
    bins = {}
    for x, y, b in _bits_points(t):
        for ori, (w, h) in (("h", (WIN_A, WIN_B)), ("v", (WIN_B, WIN_A))):
            k = (ori, int(x // w), int(y // h))
            bins[k] = bins.get(k, 0) + b
    hits = []
    for (ori, i, j), n in bins.items():
        if n < PILE_BITS:
            continue
        w, h = (WIN_A, WIN_B) if ori == "h" else (WIN_B, WIN_A)
        x0, y0, x1, y1 = i * w, j * h, (i + 1) * w, (j + 1) * h
        near = None
        for rx0, ry0, rx1, ry1, nm in rects:
            dx = max(rx0 - x1, x0 - rx1, 0.0)
            dy = max(ry0 - y1, y0 - ry1, 0.0)
            if dx <= FACE_UM and dy <= FACE_UM:
                near = nm
                break
        if near:
            hits.append((n, near, (round(x0), round(y0))))
    return sorted(hits, reverse=True)


def ft_site_legal(t):
    o = t.get("outline_um")
    if not o:
        return []
    W, H = o
    rects = G.hard_rects(t)
    hits = []
    for s in t.get("ft_slots") or []:
        if not isinstance(s, dict):
            continue
        cw, ch = (s.get("bit_site_cell_um") or [0.0, 0.0])[:2]
        pts_ = [(x, y, 0.0, 0.0) for x, y in F.pts(s.get("regs_um"))]
        for st in s.get("bit_sites_um") or []:
            pts_ += [(x, y, cw, ch) for x, y in F.pts(st)]
        bad_o = bad_c = 0
        for x, y, w, h in pts_:
            if F._over(x, y, W, H, w, h) > F.TOL:
                bad_o += 1
            elif any(x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5 for x0, y0, x1, y1, _n in rects):
                bad_c += 1
        regs = [(round(x, 2), round(y, 2)) for x, y in F.pts(s.get("regs_um"))]
        dup = len(regs) - len(set(regs))
        if bad_o or bad_c or dup:
            hits.append((s.get("name"), bad_o, bad_c, dup))
    return hits


def _per_type(check, fn, fmt, raw):
    out, n = [], 0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        v = fn(t)
        if v:
            n += 1
            out.append(_w(check, tn, f"{len(v)} finding(s):", "; ".join(fmt(x) for x in v[:MAX_EX]) + (" ..." if len(v) > MAX_EX else "")))
    return out + [_w(check, f"summary {n} types flagged (report only)")]


def _f_rank(raw, plan_path, tree=None, **_k):
    return _per_type("RANK-PILE-PINFACE", rank_pile, lambda h: f"{h[0]} bits in a {WIN_A:g}x{WIN_B:g} um window at {h[2]} by {h[1]}", raw)


def _f_ftlegal(raw, plan_path, tree=None, **_k):
    return _per_type("FT-SITE-LEGAL", ft_site_legal, lambda h: f"{h[0]} {h[1]} outside, {h[2]} in a core, {h[3]} duplicate reg(s)", raw)


def legal_gate(raw, types=None):
    """launch-gate form: WARN lines for the ft slots of the named types (all when None); a caller may refuse on any line"""
    out = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if types is not None and tn not in types:
            continue
        if isinstance(t, dict):
            out += [_w("FT-SITE-LEGAL", tn, f"{h[0]} {h[1]} outside, {h[2]} in a core, {h[3]} duplicate reg(s) (launch gate)") for h in ft_site_legal(t)]
    return out


def placed_reach(scan_path):
    """-> (stop, line): placed_scan.json bits_over_cycle > 0 (bits_over_reach > OVER_REACH_MAX when set) = a route-goal kit stops"""
    d = json.loads(Path(scan_path).read_text())
    boc, bor = int(d.get("bits_over_cycle") or 0), int(d.get("bits_over_reach") or 0)
    stop = boc > 0 or (OVER_REACH_MAX is not None and bor > OVER_REACH_MAX)
    line = _w("PLACED-REACH", f"{scan_path}: {boc} bits over one cycle ({d.get('cycle_um')} um), {bor} over reach ({d.get('limit_um')} um), "
                              f"{d.get('groups_need_station')} NEED-STATION groups -> " + ("STOP route goal" if stop else "ok"))
    return stop, line


def placed_reach_decision(scan_path, goal, environ=None):
    """-> (stop_kit, line): the stop is reported always, enforced only for goal 'route' with OT_PLACED_REACH_STOP=1"""
    env = os.environ if environ is None else environ
    stop, line = placed_reach(scan_path)
    return bool(stop and goal == "route" and env.get("OT_PLACED_REACH_STOP") == "1"), line


def launch_scope(kit):
    """kit: dict(type, goal, bound_plan_sha, wave_plan_sha, touched_types (iterable or None), signed, open_functional_row, fp_clean)"""
    out, tn = [], kit.get("type")
    if kit.get("bound_plan_sha") and kit.get("wave_plan_sha") and kit["bound_plan_sha"] != kit["wave_plan_sha"]:
        out.append(_w("LAUNCH-SCOPE", tn, f"bound plan {kit['bound_plan_sha'][:12]} != wave plan {kit['wave_plan_sha'][:12]}"))
    tt = kit.get("touched_types")
    if tt is not None and tn not in set(tt):
        out.append(_w("LAUNCH-SCOPE", tn, "type is outside the event's touched set"))
    if kit.get("goal") == "route":
        why = [k for k, bad in (("signed", kit.get("signed")), ("open functional row", kit.get("open_functional_row")),
                                 ("not FP-clean", kit.get("fp_clean") is False)) if bad]
        if why:
            out.append(_w("LAUNCH-SCOPE", tn, "route goal refused for: " + ", ".join(why)))
    return out


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_ledger(path):
    """tsv with a header containing file, sha256, owner, types, pre_verdict -> {file: row}"""
    with open(path, newline="") as f:
        out = {}
        for r in csv.DictReader(f, delimiter="\t"):
            k = r.get("file") or r.get("row_file")        # lanes/ROW-LEDGER-S81.tsv header: row_file
            if k and not k.startswith("#"):
                out[k] = r
        return out


def row_ledger(applied, ledger):
    """applied: {file: sha256}; ledger: {file: {sha256, owner, types, pre_verdict}}"""
    out = []
    for f, sha in sorted(applied.items()):
        r = ledger.get(f)
        if r is None:
            out.append(_w("ROW-LEDGER", f, "applied but not in the ledger"))
            continue
        miss = [k for k in ("owner", "types", "pre_verdict") if not (r.get(k) or "").strip()]
        if (r.get("sha256") or "") != sha:
            out.append(_w("ROW-LEDGER", f, f"ledger sha {str(r.get('sha256'))[:12]} != applied {sha[:12]}"))
        if miss:
            out.append(_w("ROW-LEDGER", f, "ledger line lacks " + ", ".join(miss)))
    return out


F2 = {"RANK-PILE-PINFACE": _f_rank, "FT-SITE-LEGAL": _f_ftlegal}
findings_by_check = {k: G._safe(k, v) for k, v in F2.items()}
