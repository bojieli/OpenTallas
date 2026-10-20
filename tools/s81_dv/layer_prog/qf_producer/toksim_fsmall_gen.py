#!/usr/bin/env python3
"""TOKSIM-S81B/FSMALL (10-19): per-frame bench vectors of the small-row field ops of ONE slice (every frame the slice
owns), from the field placement compiler of record (xs_place.compile_frame: the full multi-phase field of the frame,
every phase legalised as compiled) and the real layer fixture rows.  No new compiler logic: compile_frame + gen_one.

  toksim_fsmall_gen.py list --die-src D [--slice-index G]            frames of slice G: master, lk strap, base master
  toksim_fsmall_gen.py gen  --die-src D --layer L --frame F --fixtures FX --out OUT --ops OP...
        -> OUT/p<k>/ (meta.json, ARGS, images) for every non-empty phase of OP on frame F; OUT/frame.json summary
"""
import argparse, json, sys, types
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import xs_place as XP          # noqa: E402
import lower_xs as LX          # noqa: E402
import dv_layer_compile as C   # noqa: E402
import numpy as np             # noqa: E402

# xs_place.FMat indexes the weight with np.asarray(rows): an op chunk with NO rows on this frame (R frames of the slice)
# gives a float64 empty index -> IndexError.  Cast the row list to int (identical for every non-empty chunk).
_fm_init = XP.FMat.__init__
def _fm_init_int(self, name, fmt, arr, sc, rows, phase):
    _fm_init(self, name, fmt, arr, sc, np.asarray(rows, dtype=np.int64), phase)
XP.FMat.__init__ = _fm_init_int


def main():
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest='cmd', required=True)
    l = s.add_parser('list'); l.add_argument('--die-src', required=True); l.add_argument('--slice-index', type=int, default=0)
    g = s.add_parser('gen'); g.add_argument('--die-src', required=True); g.add_argument('--layer', required=True)
    g.add_argument('--frame', required=True); g.add_argument('--fixtures', required=True); g.add_argument('--out', required=True)
    g.add_argument('--ops', nargs='+', required=True)
    a = p.parse_args()
    die = C.Die(C.die_tree(None, a.die_src))
    if a.cmd == 'list':
        out = []
        for sl in sorted(die.slices()):
            gi = LX.slice_index(die, sl)
            if gi != a.slice_index:
                continue
            for j, fr in enumerate(die.frames_of(sl)):
                m = die.inst[fr]['master']; lk = die.strap(fr, 'lk')
                out.append(dict(slice=sl, slice_index=gi, frame=fr, frame_index=j, master=m, base=LX.base_master(m),
                                lk=lk, land_e=LX.land_e(lk)))
        print(json.dumps(out))
        return 0
    ops = XP.XS_OPS[a.layer] + XP.BF_OPS[a.layer]
    rec, field = XP.compile_frame(die, a.frame, a.fixtures, ops)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ns = types.SimpleNamespace(fixtures=a.fixtures, frame=a.frame, mutant=None, bf_measure=False)
    summ = []
    for ph in rec['phases']:
        if ph['op'] in a.ops and ph['rows'] > 0:
            if 'fmt' not in ph:     # phase 0 = attn.a_proj (lower_xs frame programme): its own generator of record
                assert ph['op'] == 'attn.a_proj' and ph['phase'] == 0, ph['op']
                LX.cmd_gen(types.SimpleNamespace(frame=a.frame, slice=None, out=str(out / 'p0'), fixtures=a.fixtures,
                                                 die_ref=None, die_src=a.die_src, cycles=LX.CYCLES, mutant=None))
                (out / 'p0' / 'CHECKER').write_text('lower_xs\n')
                ph = dict(ph, fmt='fp8', K=5120)
            else:
                XP.gen_one(ns, rec, field, ph, out / f"p{ph['phase']}")
            summ.append(dict(phase=ph['phase'], op=ph['op'], rows=ph['rows'], fmt=ph.get('fmt', 'fp8'), K=ph.get('K'),
                             seg=ph.get('seg'), nseg=ph.get('nseg'), calendar=ph.get('calendar'), faults=ph.get('faults'),
                             ret_words=ph.get('ret_words')))
    (out / 'frame.json').write_text(json.dumps(dict(layer=a.layer, frame=a.frame, master=rec['master'], lk=rec['lk'],
        base=LX.base_master(rec['master']), land_e=LX.land_e(rec['lk']), slice=rec['slice'], slice_index=rec['slice_index'],
        frame_index=rec['frame_index'], nphases=rec['nphases'], phases=summ), indent=1) + '\n')
    print('FSMALL_GEN_DONE', a.layer, a.frame, rec['master'], rec['lk'], [(x['phase'], x['op'], x['rows']) for x in summ])
    return 0


if __name__ == '__main__':
    sys.exit(main())
