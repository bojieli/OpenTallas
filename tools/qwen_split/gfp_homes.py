"""GLOBAL-FP-Q homes override for the Qwen compute die generator (OT_SPLIT_HOMES=<homes.json>).

Applied at the END of compute_spine.place(), after every placement / binding step and BEFORE the master pin
assignment, relay plan, reset tree and cuts, so all of those are derived from the overridden homes (top-down pins).

The file is schema opentallas.qwen.globalfp-homes.v1: {"homes": {inst: {"m", "x", "y", "o"[, "w", "h"]}}, ...}.
Fail-closed rules: every named instance must exist with the same master (and the same outline when w/h are
given); the orientation must be one of R0/MX/MY/R180; after the override the whole placement must have no overlap
and nothing outside the die.  Instances not named keep their generated homes.  New instances can be reserved only
through "reserve" (a named empty frame recorded for later masters, never placed as a cell).
"""
import hashlib
import json
from pathlib import Path

ORIENTS = ('R0', 'MX', 'MY', 'R180')


def _overlaps(insts, eps=1e-3):
    rs = sorted(((i.x, i.y, i.x + i.w, i.y + i.h, i.name) for i in insts))
    bad = []
    for a in range(len(rs)):
        x0, y0, x1, y1, n = rs[a]
        for b in range(a + 1, len(rs)):
            u0, v0, u1, v1, k = rs[b]
            if u0 >= x1 - eps:
                break
            if v0 < y1 - eps and v1 > y0 + eps:
                bad.append((n, k))
    return bad


def apply(model, path):
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    if d.get('schema') != 'opentallas.qwen.globalfp-homes.v1':
        raise ValueError(f'OT_SPLIT_HOMES: unexpected schema {d.get("schema")}')
    by = {i.name: i for i in model['insts']}
    unknown = sorted(set(d['homes']) - set(by))
    if unknown:
        raise ValueError(f'OT_SPLIT_HOMES: {len(unknown)} unknown instances, e.g. {unknown[:5]}')
    moved = []
    for n, h in d['homes'].items():
        i = by[n]
        if h['m'] != i.master:
            raise ValueError(f'OT_SPLIT_HOMES: {n} master {h["m"]} != generated {i.master}')
        if 'w' in h and (abs(h['w'] - i.w) > 1e-3 or abs(h['h'] - i.h) > 1e-3):
            raise ValueError(f'OT_SPLIT_HOMES: {n} outline {h["w"]}x{h["h"]} != generated {i.w}x{i.h}')
        if h['o'] not in ORIENTS:
            raise ValueError(f'OT_SPLIT_HOMES: {n} orientation {h["o"]}')
        if (round(i.x, 3), round(i.y, 3), i.orient) != (round(h['x'], 3), round(h['y'], 3), h['o']):
            moved.append(n)
        i.x, i.y, i.orient = round(float(h['x']), 4), round(float(h['y']), 4), h['o']
    W, H = model['die']['w'], model['die']['h']
    out = [i.name for i in model['insts'] if i.x < -1e-3 or i.y < -1e-3 or i.x + i.w > W + 1e-3 or i.y + i.h > H + 1e-3]
    ovl = _overlaps(model['insts'])
    if out or ovl:
        raise ValueError(f'OT_SPLIT_HOMES: {len(out)} outside {out[:4]}, {len(ovl)} overlaps {ovl[:4]}')
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), candidate=d.get('candidate'),
                moved=len(moved), moved_names=moved[:200], reserve=d.get('reserve', {}), qualified=False)
