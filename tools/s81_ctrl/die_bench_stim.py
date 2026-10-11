#!/usr/bin/env python3
"""Stimulus of the S81 die control-plane bench tb_s81_die_fld (s81-ctl-1011, 2026-10-11).

Writes, for one real stage program (tools/s81_ctrl/stage_programs.py, default S001 = L0 ffn + L1 attn, 60 jobs,
8 field phases):
  <out>/prog.txt   one line per program entry: port arg dur npred p0 p1 p2 p3 phase   (decimal; phase -1 = not fld)
                   arg = the native descriptor the program memory holds: fld -> phase id (arg[9:0]); other engines ->
                   the op index (behavioural engines in this bench)
  <out>/stim.txt   the field phases in fld program order, tb_s81ph_gather_capture format (P / C / E records,
                   gen_stim.phase: golden csum-tree partials of the canonical S81 root ownership)
"""
import argparse, json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'rtl/dsrom_sys/s81_ph/test'))
import gen_stim  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--stage', default='S001')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--programs', type=Path, default=ROOT / 'results/rtl/s81_ctrl_20261008/programs')
    a = ap.parse_args()
    p = json.loads((a.programs / f'{a.stage}.json').read_text())
    rng = random.Random(a.seed)
    a.out.mkdir(parents=True, exist_ok=True)
    lines, nph = [], 0
    with open(a.out / 'stim.txt', 'w') as f:
        for o in p['ops']:
            ps = o['preds']
            assert len(ps) <= 4, o
            ph = -1
            if o['eng'] == 'fld':
                ph = nph
                # real field phases, small enough for a die bench (64..300 rows, np 0..3, all three formats)
                gen_stim.phase(rng, f, ph, rng.choice([64, 128, 256, 300]), rng.choice([0, 1, 3]), nph % 3,
                               burst=rng.random() < 0.5, maxseg=4)
                nph += 1
            arg = ph if ph >= 0 else o['op']
            lines.append(' '.join(str(v) for v in [o['port'], arg, o['dur'], len(ps)] + (ps + [0] * 4)[:4] + [ph]))
    (a.out / 'prog.txt').write_text('\n'.join(lines) + '\n')
    print(f"{a.stage}: {len(lines)} ops, {nph} field phases -> {a.out}")


if __name__ == '__main__':
    main()
