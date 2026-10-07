#!/usr/bin/env python3
"""S81 die: routing utilisation per floorplan region from a GRT case (CLAUDE S81-RERUN 2026-10-07, OWNER rule 3:
corridors and regions at ~55-60 %).  gcell_usage.txt windows (baseline-subtracted with the empty-net case) are
classified with tools/dsrom_s81_fulldie.where(); per region and layer: mean use/cap, p90, max, windows.

  region_util.py --work CASE --base BASE_CASE --s81-opts "<die options>" --die layer --out util.json
"""
import argparse, json, shlex, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--base', type=Path)
    ap.add_argument('--s81-opts', required=True)
    ap.add_argument('--die', default='layer')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(shlex.split(a.s81_opts) + ['--die', a.die]))
    m = S.build()
    lines = (a.work / 'gcell_usage.txt').read_text().splitlines()
    gx = [float(v) for v in lines[0].split()[1].split(',')]
    gy = [float(v) for v in lines[1].split()[1].split(',')]
    dbu = 1000.0 if max(gx) > S.DIE[0] * 2 else 1.0
    gx, gy = [v / dbu for v in gx], [v / dbu for v in gy]
    bl = {}
    if a.base:
        for line in (a.base / 'gcell_usage.txt').read_text().splitlines():
            if line.startswith('L '):
                fs = line.split()
                bl[(fs[1], int(fs[2]))] = [tuple(float(x) for x in c.split('/')) for c in fs[3:]]
    acc = defaultdict(lambda: dict(cap=0.0, use=0.0, r=[]))
    for line in lines:
        if not line.startswith('L '):
            continue
        fs = line.split()
        ln, j = fs[1], int(fs[2])
        if ln in ('M1', 'M2', 'M3'):
            continue
        brow = bl.get((ln, j))
        for i, c in enumerate(fs[3:]):
            cap, use = (float(x) for x in c.split('/'))
            if brow:
                cap, use = cap - brow[i][1], use - brow[i][1]
            if cap <= 0:
                continue
            x, y = gx[min(len(gx) - 1, 4 * i)], gy[min(len(gy) - 1, j)]
            k = S.where(m, x + 2 * (gx[1] - gx[0]), y + 2 * (gy[1] - gy[0]))
            for key in ((k, ln), (k, 'M4-M9')):
                e = acc[key]
                e['cap'] += cap
                e['use'] += use
                e['r'].append(use / cap)
    out = {}
    for (k, ln), e in sorted(acc.items()):
        r = sorted(e['r'])
        out.setdefault(k, {})[ln] = dict(mean=round(e['use'] / e['cap'], 3), p90=round(r[int(0.9 * (len(r) - 1))], 3),
                                         p99=round(r[int(0.99 * (len(r) - 1))], 3), max=round(r[-1], 3), windows=len(r))
    a.out.write_text(json.dumps(dict(case=str(a.work), opts=a.s81_opts, die=a.die, regions=out), indent=1) + '\n')
    for k, v in out.items():
        t = v.get('M4-M9', {})
        worst = max((vv['p90'], ln) for ln, vv in v.items() if ln != 'M4-M9')
        print(f"{k:12s} mean {t.get('mean')} p90 {t.get('p90')} p99 {t.get('p99')} max {t.get('max')}  worst-layer p90 {worst}")


if __name__ == '__main__':
    main()
