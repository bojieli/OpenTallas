#!/usr/bin/env python3
"""Token cost of the S81 static return node r2 (S-NET 2026-10-15: +3 fixed pipeline edges per node level, PIPE_C 7 -> 10).

Every field phase (eng 'fld') returns its partials through the frame's ragged return tree; the tree over 2 x pairs leaves
(tools/dsrom_s81_fulldie.py return_tree, 17..48 leaves a frame) is 5..6 node levels deep, so a field phase's done moves
by +3 x levels (worst frame 6 levels -> +18).  The cost is composed on the compiler's own stage programs
(results/rtl/s81_ctrl_20261008/programs, golden ASAP: start = max(ext, preds' end), the exact rule of
tools/s81_ctrl/stage_programs.py; the recomposition reproduces every committed makespan) with each fld duration + delta.
Output: per-stage makespans and the token delta (sum over the 59 stage programs, AR, one token)."""
import argparse
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def makespan(ops, fld_extra=0):
    en = []
    for o in ops:
        s = max([o['ext']] + [en[p] for p in o['preds']])
        en.append(s + o['dur'] + (fld_extra if o['eng'] == 'fld' else 0))
    return max(en) if en else 0


def compose(progdir, levels, per_level):
    extra = levels * per_level
    rows = []
    for f in sorted(glob.glob(str(Path(progdir) / 'S*.json'))):
        d = json.loads(Path(f).read_text())
        m0 = makespan(d['ops'])
        if m0 != d['makespan']:
            raise SystemExit(f'{f}: recomposition {m0} != committed makespan {d["makespan"]}')
        rows.append(dict(stage=d['stage'], layers=d.get('layers'), fld_phases=sum(o['eng'] == 'fld' for o in d['ops']),
                         makespan=m0, delta=makespan(d['ops'], extra) - m0))
    base = sum(r['makespan'] for r in rows)
    delta = sum(r['delta'] for r in rows)
    return dict(levels=levels, edges_per_level=per_level, fld_extra=extra, token_cycles=base, token_delta=delta,
                e2e_loss_pct=round(100.0 * delta / (base + delta), 3), stages=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--programs', default=str(ROOT / 'results/rtl/s81_ctrl_20261008/programs'))
    ap.add_argument('--levels', type=int, default=6)
    ap.add_argument('--per-level', type=int, default=3)
    ap.add_argument('--out')
    a = ap.parse_args()
    r = compose(a.programs, a.levels, a.per_level)
    s = json.dumps(r, indent=1)
    if a.out:
        Path(a.out).write_text(s + '\n')
    print(f"levels {r['levels']} x {r['edges_per_level']} = +{r['fld_extra']} per field phase: token {r['token_cycles']} "
          f"+{r['token_delta']} cycles = {r['e2e_loss_pct']} %")


if __name__ == '__main__':
    main()
