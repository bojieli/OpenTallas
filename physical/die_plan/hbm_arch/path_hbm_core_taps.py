#!/usr/bin/env python3
"""Re-derive stale HBM SU early core clock taps from the CURRENT core placement (orient-aware).

b2n.exp_lane() places one early core tap beside each lane_exp core's clock-pin cluster (origin + mean clock-pin
xy, then schema.tap_clear), but it ignores the core orient, and the later SU corridor / bank-channel core
re-placements moved q_su00/01/10/11 cores without re-deriving their taps. Result in plan B1: SU core taps sit
200-460 um from their clock pins, and q_su11 u_su_Q1_lane_exp13's tap is outside the outline (G0 clock ERR).

Rule (same as exp_lane, plus the orient that check.py core_faces applies): tap = core origin + mean of the core's
clock-port pins (core frame, MY/MX/R180 applied), then tap_clear(clear=4.32) against cores and the other taps.
Default: only ILLEGAL kind=core taps are moved (outside the outline, or on a hard-core box); --tol T moves every
core tap more than T um from its clock-pin cluster. All taps > 25 um from their cluster are listed in the report
(far_taps): with the SU cores abutting each other, tap_clear finds no channel near many clock-pin clusters (a core
placement item for CLOCK / the SU re-place, not fixed here). name, insertion_ps and budget_owner are unchanged.
"""
import argparse, json, re, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / 'tools' / 'die_plan')]
import schema as S

CLOCK_PORTS = {'clk', 'ck', 'clock', 'clk_bank', 'clk_bank_macro', 'clk_insert', 'clk_lane', 'clk_side'}


def to_type(hc, x, y):
    cw, ch = hc['outline_um']; o = hc.get('orient', 'R0'); ox, oy = hc['origin_um']
    if o in ('MY', 'R180'): x = cw - x
    if o in ('MX', 'R180'): y = ch - y
    return ox + x, oy + y


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--types', default='q_su00,q_su01,q_su10,q_su11'); ap.add_argument('--tol', type=float, default=None)
    a = ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    p = json.loads((a.src / 'die_plan.json').read_text()); rep = []; far = []
    for tn in a.types.split(','):
        t = p['partition_types'][tn]; hcs = {h['inst']: h for h in t.get('hard_cores', [])}
        taps = t.get('clock', {}).get('taps', [])
        for tp in taps:
            ci, _, port = tp['name'].partition('.')
            hc = hcs.get(ci)
            if tp.get('kind') != 'core' or not hc or not hc.get('pins_file'): continue
            pins = json.loads((a.src / hc['pins_file']).read_text())
            ck = [q for q in pins if (q['name'] == port if port else re.sub(r'\[\d+\]$', '', q['name']) in CLOCK_PORTS)]
            if not ck: raise SystemExit(f'{tn}.{tp["name"]}: no clock pin in {hc["pins_file"]}')
            xs = [to_type(hc, q['x'], q['y']) for q in ck]
            cx = sum(u for u, _ in xs) / len(xs); cy = sum(v for _, v in xs) / len(xs)
            d = abs(cx - tp['xy'][0]) + abs(cy - tp['xy'][1]); w, h = t['outline_um']; tx, ty = tp['xy']
            illegal = not (0 <= tx <= w and 0 <= ty <= h) or any(
                x0 < tx < x1 and y0 < ty < y1 for x0, y0, x1, y1 in S.placed_macro_boxes(t).values())
            if d > 25: far.append(dict(type=tn, tap=tp['name'], xy=tp['xy'], pins_xy=[round(cx, 1), round(cy, 1)], d_um=round(d, 1)))
            if not (illegal or (a.tol is not None and d > a.tol)): continue
            x, y = S.tap_clear(t, cx, cy, [tuple(o['xy']) for o in taps if o is not tp], clear=4.32)
            old = list(tp['xy']); tp['xy'] = [round(x, 4), round(y, 4)]
            tp['note'] = (tp.get('note', '') + f' | path_hbm_core_taps: re-derived from current core placement + orient '
                          f'(clock pins {len(ck)} at {cx:.1f},{cy:.1f}); was {old}').lstrip(' |')
            rep.append(dict(type=tn, tap=tp['name'], before=old, after=tp['xy'], pins_xy=[round(cx, 3), round(cy, 3)]))
    shutil.copytree(a.src, a.out)
    (a.out / 'die_plan.json').write_text(json.dumps(p, indent=1) + '\n')
    (a.out / 'core_taps_report.json').write_text(json.dumps(dict(moved=rep, far_taps_before=far), indent=1) + '\n')
    print(json.dumps({'moved': rep, 'far_taps': len(far)}))


if __name__ == '__main__': main()
