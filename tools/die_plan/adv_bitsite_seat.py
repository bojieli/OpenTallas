"""adv_bitsite_seat.py -- PRECHECK ADV-BITSITE-SEAT (COORD 11-24 02:4x, r703; report only).

A station moved (regs_um edited, RREACH / street re-site / unbury) while its exact bit sites (bit_sites_um / face_bit_sites_um) stayed
where they were: KV A5t2 RREACH 39 entries up to 659 um off crashed emit; KV in-core 3 bit patterns ~40 um off gave 2 G0 errors.

Per ft slot with bit_sites_um (reusing ft_bit_sites.validate_slot for the count / shape rules) and per internal_stations row with
bit_sites_um / face_bit_sites_um:
  COUNT   stage count must be stations-1 (or stations with explicit_stage0) for ft slots; len(regs_um) or len(regs_um)-1 for in-core rows
  SEAT    for each stage j, the station point regs_um[j + off] (off = 1 for stations-1 stages, 0 for explicit_stage0 / len==regs) must lie
          within TOL_UM (Manhattan distance to the stage's site bounding box) -- N is not fixed by any plan rule: the stage's sites are the
          cell grid of one station (cell 1.404 x 0.27 um, a station spans a few um to its bit columns), so 10 um separates a seated station
          from a moved one; override with kw tol_um / env OT_ADV_BITSITE_TOL_UM.
Per type: stages checked / stages off, worst um.  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import math
import os
import sys
from pathlib import Path

CHECK = "ADV-BITSITE-SEAT"
TOL_UM = 10.0
STRONG_UM = 40.0     # a line is printed only above this; 10-40 um is counted (A5s: 298 stages > 10 um, mostly spread clusters)
MAX_LINES = 25


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def bbox_dist(stage, p):
    xs = [q[0] for q in stage]
    ys = [q[1] for q in stage]
    return max(min(xs) - p[0], 0.0, p[0] - max(xs)) + max(min(ys) - p[1], 0.0, p[1] - max(ys))


def judge_stages(stages, regs, off, tol=TOL_UM):
    """-> [(stage j, dist)] stages whose station point is farther than tol from the stage's site bounding box"""
    bad = []
    for j, st in enumerate(stages):
        if not st or j + off >= len(regs):
            continue
        d = bbox_dist(st, regs[j + off])
        if d > tol:
            bad.append((j, d))
    return bad


def check_ft(slot, tol):
    """-> ('COUNT', msg) | ('SEAT', [(j, d)], n_stages) | None"""
    try:
        import ft_bit_sites as FB
        FB.validate_slot(slot)
    except ImportError:
        pass
    except ValueError as e:
        return ("COUNT", str(e))
    bs, regs = slot.get("bit_sites_um"), slot.get("regs_um")
    if not bs or not regs:
        return None
    off = 0 if (slot.get("explicit_stage0") is True and len(bs) == slot.get("stations", 1)) else 1
    bad = judge_stages(bs, regs, off, tol)
    return ("SEAT", bad, len(bs)) if bad else None


def check_row(e, tol):
    bs = e.get("bit_sites_um") or e.get("face_bit_sites_um")
    regs = e.get("regs_um")
    if not bs or not regs:
        return None
    if len(bs) not in (len(regs), len(regs) - 1):
        return ("COUNT", f"{len(bs)} stages for {len(regs)} stations (need {len(regs)} or {len(regs) - 1})")
    bad = judge_stages(bs, regs, 0 if len(bs) == len(regs) else 1, tol)
    return ("SEAT", bad, len(bs)) if bad else None


NOSITE_RE = os.environ.get('OT_ADV_BITSITE_NOSITE_RE', 'st_b_v2')    # types whose NOSITE line is printed (census confirmed 41-61 types share the pattern, only these are known bad)
NOSITE_BITS = 1000    # a type whose internal station rows WITHOUT exact sites total >= this is listed (QC sle_st_b_v2 C1g: 3 rows / 1427 bits)


def nosite_bits(t):
    """(unsited bits, unsited rows, rows) of one type's internal_stations: rows with regs_um but no bit_sites_um / face_bit_sites_um"""
    bits = n = rows = 0
    for e in t.get("internal_stations") or []:
        if not isinstance(e, dict) or not e.get("regs_um"):
            continue
        rows += 1
        if not (e.get("bit_sites_um") or e.get("face_bit_sites_um")):
            n += 1
            bits += int(e.get("bits") or 1)
    return bits, n, rows


def seated_map(raw, tol):
    """{(type, key): {stage j: dist}} for every ft slot / row with exact sites (baseline: which stages WERE seated)"""
    m = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        if not isinstance(t, dict):
            continue
        for s in t.get("ft_slots") or []:
            bs, regs = (s.get("bit_sites_um"), s.get("regs_um")) if isinstance(s, dict) else (None, None)
            if bs and regs:
                off = 0 if (s.get("explicit_stage0") is True and len(bs) == s.get("stations", 1)) else 1
                m[(tn, f"ft {s.get('name')}")] = {j: bbox_dist(st, regs[j + off]) for j, st in enumerate(bs) if st and j + off < len(regs)}
        for e in t.get("internal_stations") or []:
            bs, regs = (e.get("bit_sites_um") or e.get("face_bit_sites_um"), e.get("regs_um")) if isinstance(e, dict) else (None, None)
            if bs and regs and len(bs) in (len(regs), len(regs) - 1):
                off = 0 if len(bs) == len(regs) else 1
                m[(tn, str(e.get("conn")))] = {j: bbox_dist(st, regs[j + off]) for j, st in enumerate(bs) if st and j + off < len(regs)}
    return m


def _findings(raw, plan_path, tree=None, **kw):
    base = kw.get("baseline")
    bmap = None
    if base:
        import json as _j
        braw = base if isinstance(base, dict) else _j.loads(Path(base).read_text())
        bmap = seated_map(braw, float(kw.get("tol_um") or TOL_UM))
    tol = float(kw.get("tol_um") or os.environ.get("OT_ADV_BITSITE_TOL_UM") or TOL_UM)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    types = raw.get("partition_types") or {}
    used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    strong_um = float(kw.get('strong_um') or os.environ.get('OT_ADV_BITSITE_STRONG_UM') or STRONG_UM)
    out, nst, nbad, ntypes, ncount, nweak = [], 0, 0, 0, 0, 0
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or (used and tn not in used):
            continue
        res = []
        for s in t.get("ft_slots") or []:
            r = check_ft(s, tol) if isinstance(s, dict) else None
            if r:
                res.append((f"ft {s.get('name')}", r))
        for e in t.get("internal_stations") or []:
            r = check_row(e, tol) if isinstance(e, dict) else None
            if r:
                res.append((str(e.get("conn")), r))
        if not res:
            continue
        nweak += sum(1 for _, r in res if r[0] == "SEAT" for _, d in r[1] if d <= strong_um)
        res = [(n, (r[0], [x for x in r[1] if x[1] > strong_um and (bmap is None or bmap.get((tn, n), {}).get(x[0], 1e9) <= tol)], r[2])) if r[0] == "SEAT" else (n, r) for n, r in res]
        res = [x for x in res if x[1][0] == "COUNT" or x[1][1]]
        if not res:
            continue
        ntypes += 1
        cnt = [x for x in res if x[1][0] == "COUNT"]
        seat = [x for x in res if x[1][0] == "SEAT"]
        ncount += len(cnt)
        nbad += sum(len(x[1][1]) for x in seat)
        worst = max((d for _, r in seat for _, d in r[1]), default=0.0)
        w = max(seat, key=lambda x: max(d for _, d in x[1][1]), default=None)
        out.append((worst + 1000 * len(cnt), _w(f"{tn}: {len(seat)} slot/row(s) with stations off their bit sites ({sum(len(x[1][1]) for x in seat)} stages, worst {worst:.0f} um at "
                    f"{w[0] if w else '-'} stage {max(w[1][1], key=lambda z: z[1])[0] if w else '-'}), {len(cnt)} with a wrong stage count"
                    f"{' (' + cnt[0][0] + ': ' + cnt[0][1][1][:90] + ')' if cnt else ''}; the station moved and its exact sites stayed; fix: re-seat bit_sites_um on regs_um")))
    nobit = float(kw.get("nosite_bits") or os.environ.get("OT_ADV_BITSITE_NOSITE_BITS") or NOSITE_BITS)
    nos = []
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or (used and tn not in used):
            continue
        b, n, rows = nosite_bits(t)
        has_exact = any(isinstance(x, dict) and x.get("bit_sites_um") for x in t.get("ft_slots") or []) or \
            any(isinstance(x, dict) and (x.get("bit_sites_um") or x.get("face_bit_sites_um")) for x in t.get("internal_stations") or [])
        if b >= nobit and has_exact:                          # MIXED: the type pins some stations by exact sites and leaves 1000+ bits to the placer
            nos.append((b, tn, n, rows))
    nos.sort(reverse=True)
    import re as _re
    rx = _re.compile(str(kw.get('nosite_re') or NOSITE_RE))
    for b, tn, n, rows in [x for x in nos if rx.search(x[1])][:MAX_LINES]:
        out.append((-1, _w(f"{tn}: NOSITE {n} of {rows} internal station row(s) have no exact bit sites ({b:,} bits, bit_route per_bit) while the type's other stations DO have exact sites: the placer picks these and can fold the relay chains "
                            f"(QC sle_st_b_v2 C1g: 28 paths > 405 um, empty taps); the same mixed form is in {len(nos)} types, so only types matching /{rx.pattern}/ (the known bad ones) are printed; a type with NO exact sites anywhere is normal and not counted")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES * 2]]
    lines.append(_w("summary", f"{ntypes} type(s) flagged, {nbad} stage(s) farther than {strong_um:g} um from their station (+{nweak} between {tol:g} and {strong_um:g} um, counted only), "
                               f"{ncount} stage-count error(s), {len(nos)} type(s) with >= {nobit:g} unsited station bits (NOSITE, printed only for /{rx.pattern}/) (thresholds are my pick, not a plan rule){'; MOVED-SINCE-BASELINE only (stages seated in the baseline, off now)' if bmap is not None else '; no baseline: includes stages that were already off'}"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], baseline=sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
