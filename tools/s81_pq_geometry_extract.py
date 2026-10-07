#!/usr/bin/env python3
"""Geometry extract for the S81 PQ full-shape design (Claude, 2026-10-07).

Builds the actual 1792-pair layer die with the die generator (Python build() + finalize_r8() only, no ORFS) and writes
the hub, end-block, column-FIFO, station and region geometry the design tool reads.  --generator selects the generator
file (the pinned historical copy or the current tools/dsrom_s81_fulldie.py); its sha256 is recorded.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTS = ('--gen r8 --rev r9 --elem-h 198.72 --q-elem-h 183.60 --cc-reach-um 215 --vch-interleave --link-fix '
        '--corr-interleave --hop-fix --meso-d8 --cfifo-v2 --hc-xface --link-split --sel-xstg --pin-relay --ch-heights '
        '259.2,302.4,388.8,388.8,302.4,259.2,259.2 --bf-per-region 4 --geometry-fix --vm-face-mm2 2.659905216 '
        '--vch-w 1641.6 --hc-corr 1512 --pairs 1792 --die layer')


def extract(gen, base_commit):
    sys.path.insert(0, str(ROOT / 'tools'))
    # executed as tools/dsrom_s81_fulldie.py (its ROOT = parents[1] must resolve to this checkout), source from `gen`
    import types
    F = types.ModuleType('dsrom_s81_fulldie')
    F.__file__ = str(ROOT / 'tools/dsrom_s81_fulldie.py')
    sys.modules['dsrom_s81_fulldie'] = F
    exec(compile(Path(gen).read_text(), F.__file__, 'exec'), F.__dict__)
    ap = argparse.ArgumentParser()
    F.die_options(ap)
    a = ap.parse_args(OPTS.split())
    F.apply_options(a)
    m = F.build()
    F.finalize_r8(m)
    I = [dict(n=it.name, m=it.master, k=it.kind, x=it.x, y=it.y, w=it.w, h=it.h) for it in m['insts']]
    keep = lambda i: i['k'] in ('hub', 'hend', 'cfifo', 'ctrl') or i['n'].startswith(('f_x', 't0_'))
    insts = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in i.items()} for i in I if keep(i)]
    st = [i for i in I if i['k'] == 'stn' and i['n'].startswith('f_x')]
    ss = [i for i in I if i['k'] == 'sstn']
    kc, ka = collections.Counter(), collections.Counter()
    for i in I:
        kc[i['k']] += 1
        ka[i['k']] += i['w'] * i['h']
    geo = {k: v for k, v in m['geo'].items() if k != 'col_x'}
    return dict(schema='opentallas.s81.pq-fullshape.geometry-extract.v1',
        generator=str(Path(gen).resolve().relative_to(ROOT)), generator_sha256=hashlib.sha256(Path(gen).read_bytes()).hexdigest(),
        base_commit=base_commit, options=OPTS,
        note='actual mixed 1792 mapping die (512 BF + 1280 q pairs, 14 a region); python build()+finalize_r8() only, no ORFS',
        die_um=list(F.DIE), pairs=F.PAIRS, bf_pairs=F.BF_PAIRS, slots=F.SLOTS8, frame_h=F.FRAME_H8,
        tier_cols=list(F.TIER_COLS8), lane_bits=F.LSW, column_return_bits=F.CRET, geo=geo,
        regions=[r for r in m['regions'] if r['kind'] != 'field'],
        frames=[dict(name=r['name'], rect=[round(v, 3) for v in r['rect']]) for r in m['regions'] if r['kind'] == 'field'],
        hub_and_ends=[i for i in insts if i['k'] in ('hub', 'hend', 'ctrl')],
        cfifo=[i for i in insts if i['k'] == 'cfifo'],
        x_chain_stations=dict(count=len(st), area_um2=round(sum(i['w'] * i['h'] for i in st), 1), master_example=st[0]['m']),
        slot_stations=dict(count=len(ss), area_um2=round(sum(i['w'] * i['h'] for i in ss), 1), wh=[ss[0]['w'], ss[0]['h']]),
        kind_totals_mm2={k: round(v / 1e6, 3) for k, v in sorted(ka.items(), key=lambda x: -x[1])},
        kind_counts=dict(sorted(kc.items())))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--generator', type=Path, default=ROOT / 'tools/dsrom_s81_fulldie.py')
    ap.add_argument('--base-commit', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    d = extract(a.generator, a.base_commit)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(d, indent=1) + '\n')
    print(a.out, d['generator_sha256'][:12], d['pairs'], d['slots'], d['lane_bits'])


if __name__ == '__main__':
    main()
