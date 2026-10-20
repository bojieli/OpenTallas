#!/usr/bin/env python3
"""S81-ROMOPT-C (10-20): parallel legaliser search for k-class phase shapes (OT_XS_KSLOT=k) -> compiler data
tools/s81_dv/layer_prog/kslot_layouts.json, reused by frame_return_plan.plan_phase for every phase of the same shape.

A k-class phase's return calendar depends only on the frame master (topology, x station offsets), the phase shape
(fmt, K, nseg -> class last beats), the super-row count and k -- never on the weights or x values (the tree merges by
tags and arrival edges).  So one fault-free layout per shape serves every phase, frame and layer of that shape; the
compiler still re-composes it per phase and falls back to its own search when the layout does not compose clean.

    kslot_search.py --frame u_f_3L01 --op ffn.experts_gu --fixtures D --die-src S --out layouts.json [--workers 32]
                    [--iters 40000] [--rounds 4]
(release compile flags and OT_XS_KSLOT in the environment; merges into an existing --out)
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xs_place as X  # noqa: E402
import frame_return_plan as P  # noqa: E402

MODEL = {}


def _work(arg):
    key, seed, iters, W, T0, init = arg
    m = MODEL[key]
    os.environ['OT_XS_KSLOT_W'], os.environ['OT_XS_KSLOT_T0'] = str(W), str(T0)
    ini = None if init is None else {int(q): [tuple(x) for x in v] for q, v in init.items()}
    assign, f, w = P.legalise_k(m['topo'], m['pairs'], m['nsr'], m['nseg'], m['k'], m['emit'], m['vals'], seed, iters,
                                init=ini)
    return key, f, w, {str(q): [[R, s] for R, s, _ in v] for q, v in assign.items()}, (seed, iters, W, T0)


def shapes(a):
    """one representative (mat, pairs, ...) per k-class shape of the op on this frame"""
    import dv_layer_compile as C
    import lower_xs as LX
    import v41_die_images_w17w10 as I
    import frame_bench as B
    import v41_rom_ksplit_bankmap as S
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    rec, field = X.compile_frame(die, a.frame, a.fixtures, [a.op], iters=0)
    master = LX.base_master(rec['master'])
    lk = rec['lk']
    fx = X.Fix(a.fixtures)
    groups = X.op_groups(fx, a.op)
    out = {}
    for ph in rec['phases']:
        if ph['op'] != a.op or not ph.get('kslot'):
            continue
        grp = groups[ph['gi']]
        mat = X.make_mat(fx, grp, ph['sel'], a.op)
        nsr = -(-mat.rows // 2)
        st = X.KSLOT_STRETCH.get(a.op)
        key = P.kslot_key(master, mat.fmt, mat.K, ph['nseg'], nsr, ph['kslot'], st, mat.rows)
        if key in out:
            continue
        pairs = list(rec['pairs'])
        # the plan's own model (emission rule, values) -- iters 0 returns the initial layout
        sx = X.ELEM_SEG.get((mat.fmt, mat.K, ph['nseg']))
        topo = P.load_topology(master)
        off, e0 = P.emission(master)
        e0 += P.x_shift(LX.land_e(lk))
        pl = P.plan_phase(master, pairs, mat, grp['x'], ph['nseg'], iters=0, land_e=LX.land_e(lk), seg_extra=sx,
                          kslot=ph['kslot'], nsr=nsr, stretch=st)
        em = pl['emission']
        beat, sx_ = em['last_beat'], em['seg_extra']

        def emit(p, s, j=0, n=1, e0=em['e0'], off=em['off'], beat=beat, sx_=sx_):
            return e0 + beat[s] + off[p] + sx_[s]
        vals = {int(r): v for r, v in pl['rows_vals'].items()}
        out[key] = dict(topo=topo, pairs=pairs, nsr=nsr, nseg=ph['nseg'], k=ph['kslot'], emit=emit, vals=vals,
                        initial_faults=pl['faults'], phase=ph['phase'])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--frame', required=True)
    ap.add_argument('--op', required=True)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--die-src')
    ap.add_argument('--die-ref')
    ap.add_argument('--out', required=True)
    ap.add_argument('--workers', type=int, default=32)
    ap.add_argument('--iters', type=int, default=40000)
    ap.add_argument('--rounds', type=int, default=4)
    ap.add_argument('--seed0', type=int, default=0, help='seed base (parallel jobs of one shape use different bases)')
    a = ap.parse_args(argv)
    t0 = time.time()
    MODEL.update(shapes(a))
    out = Path(a.out)
    db = json.loads(out.read_text()) if out.exists() else dict(schema='opentallas.s81_dv.kslot_layouts.v1', layouts={}, provenance={})
    sched = [(20, 10), (10, 10), (20, 5), (40, 10)]
    for key, m in MODEL.items():
        if key in db['layouts']:
            print('KSLOT_SEARCH_HAVE', key, flush=True)
            continue
        best = None
        for rd in range(a.rounds):
            # round 0 from the initial layout; later rounds: half the workers restart from the best layout so far
            args = [(key, a.seed0 + 1000 * rd + i, a.iters, *sched[i % len(sched)],
                     best[3] if best is not None and i % 2 else None) for i in range(a.workers)]
            with mp.get_context('fork').Pool(a.workers) as pool:
                res = pool.map(_work, args)
            for r in res:
                if best is None or (r[1], r[2]) < (best[1], best[2]):
                    best = r
            print('KSLOT_SEARCH', key, 'round', rd, 'best faults', best[1], 'root words', best[2], 'cfg', best[4],
                  'time', round(time.time() - t0), flush=True)
            if best[1] == 0:
                break
        if best[1] == 0:
            db['layouts'][key] = best[3]
            db['provenance'][key] = dict(frame=a.frame, op=a.op, phase=m['phase'], root_words=best[2], search=best[4],
                                         initial_faults=m['initial_faults'], env={k: os.environ.get(k) for k in (
                                             'OT_XS_QPAIRS', 'OT_XS_GU_MERGE', 'OT_XS_TOPO', 'OT_XS_PROP', 'OT_XS_KSLOT', 'OT_XS_KSLOT_STRETCH')})
            out.write_text(json.dumps(db, indent=1, sort_keys=True) + '\n')
        else:
            print('KSLOT_SEARCH_NO_LAYOUT', key, 'best faults', best[1], flush=True)
    print('KSLOT_SEARCH_DONE', sorted(db['layouts']), flush=True)


if __name__ == '__main__':
    main()
