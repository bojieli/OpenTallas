#!/usr/bin/env python3
"""TOKSIM-S81C/FSGU (10-19): ffn.experts_gu frame vectors of ONE frame for ANY fixture layer (L0 / L2 / L14 / L20).

Identical to toksim_fgu_gen.py (TOKSIM-S81B/FGU) except that the field is the production phase list of the given
layer (xs_place.XS_OPS[L] + BF_OPS[L]: e.g. L2 adds attn.idx.q + attn.cmp.wk, L14 adds eng.wkv) and only ffn.experts_gu
is written: xs_place.compile_frame of the frame's full multi-phase field (real rank-0 rows of the layer fixture, every
phase legalised), one xs_place vector per non-empty experts_gu phase (p<k>/), the swap / shift mutants of its first phase,
and the phase SEQUENCE vector seq_experts_gu/ for tb_toksim_fgu_seq.sv.  No RTL, no compiler change.

    toksim_fsgu_gen.py --layer L2 --frame u_f_0L00 --fixtures FIX --die-src DIE --out VEC [--ops ffn.experts_gu]
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import xs_place as XP  # noqa: E402
import lower_xs as LX  # noqa: E402
import numpy as np  # noqa: E402

# as toksim_fsmall_gen.py: an op chunk with no rows on a frame gives a float64 empty index; cast rows to int
_fm_init = XP.FMat.__init__


def _fm_init_int(self, name, fmt, arr, sc, rows, phase):
    _fm_init(self, name, fmt, arr, sc, np.asarray(rows, dtype=np.int64), phase)


XP.FMat.__init__ = _fm_init_int
OP = 'ffn.experts_gu'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--layer', required=True)
    p.add_argument('--frame', default='u_f_0L00')
    p.add_argument('--fixtures', required=True)
    p.add_argument('--die-src', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--ops', nargs='*', default=None,
                   help='field op list (default XS_OPS[L] + BF_OPS[L]); a reduced fixture (toksim_fsgu_ffnfix.py) -> ffn.experts_gu')
    a = p.parse_args()
    import dv_layer_compile as C
    meta = json.loads((Path(a.fixtures) / 'meta.json').read_text())
    assert meta['layer'] == a.layer.rstrip('r'), (meta['layer'], a.layer)   # L0r = the reduced L0 control
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    die = C.Die(C.die_tree(None, a.die_src))
    ops = a.ops or (XP.XS_OPS[a.layer.rstrip('r')] + XP.BF_OPS[a.layer.rstrip('r')])
    rec, field = XP.compile_frame(die, a.frame, a.fixtures, ops, iters=LX.ITERS)
    ns = argparse.Namespace(fixtures=a.fixtures, frame=a.frame, mutant=None, bf_measure=False)
    phs = [ph for ph in rec['phases'] if ph['op'] == OP and ph['rows'] > 0]
    for ph in phs:
        assert ph['calendar'] == 'measured_class' and ph['faults'] == 0, (ph['phase'], ph['calendar'], ph['faults'])
        XP.gen_one(ns, rec, field, ph, out / f'p{ph["phase"]}')
    d0 = out / f'p{phs[0]["phase"]}'
    m0 = json.loads((d0 / 'meta.json').read_text())
    for ph in phs[1:]:
        mk = json.loads((out / f'p{ph["phase"]}' / 'meta.json').read_text())
        assert mk['images'] == m0['images'], ('field images differ across phases', ph['phase'])
        assert sha(out / f'p{ph["phase"]}' / 'vm.hex') == sha(d0 / 'vm.hex'), ('x differs across phases', ph['phase'])
    sd = out / 'seq_experts_gu'
    if sd.exists():
        shutil.rmtree(sd)
    shutil.copytree(d0, sd)
    (sd / 'meta.json').unlink()
    (sd / 'ARGS').unlink()
    (sd / 'seq.hex').write_text(''.join(f'{(ph["rows"] << 16) | ph["phase"]:08x}\n' for ph in phs))
    (sd / 'seq.json').write_text(json.dumps(dict(op=OP, layer=a.layer, frame=a.frame, phases=[ph['phase'] for ph in phs],
                                                 rows=[ph['rows'] for ph in phs], K=m0['K'],
                                                 vectors=[f'p{ph["phase"]}' for ph in phs]), indent=1) + '\n')
    for m in ('swap', 'shift'):
        XP.gen_one(argparse.Namespace(fixtures=a.fixtures, frame=a.frame, mutant=m, bf_measure=False), rec, field, phs[0],
                   out / f'm_{m}_p{phs[0]["phase"]}')
    idx = dict(layer=a.layer, kind=meta.get('kind'), experts=meta.get('experts'), frame=a.frame, master=rec['master'],
               lk=rec['lk'], slice=rec['slice'], frame_index=rec['frame_index'], nphases=rec['nphases'], ops=ops,
               field_ops=[(ph['phase'], ph['op'], ph['rows']) for ph in rec['phases']],
               experts_gu=dict(phases=[ph['phase'] for ph in phs], rows=[ph['rows'] for ph in phs],
                               mats=[ph['mat'] for ph in phs], nseg=sorted({ph['nseg'] for ph in phs}),
                               fmt=sorted({ph['fmt'] for ph in phs}), K=sorted({ph['K'] for ph in phs})),
               fixture_meta_sha256=sha(Path(a.fixtures) / 'meta.json'))
    (out / 'index.json').write_text(json.dumps(idx, indent=1) + '\n')
    print('TOKSIM_FSGU_GEN', a.layer, a.frame, rec['nphases'], json.dumps(idx['experts_gu']))


if __name__ == '__main__':
    main()
