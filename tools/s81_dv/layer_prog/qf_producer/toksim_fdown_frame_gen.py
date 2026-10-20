#!/usr/bin/env python3
"""TOKSIM-S81B/FDOWN (10-19): frame vectors for EVERY ffn.down phase (shared + the 6 routed experts) of one die frame.

Same method as toksim_fgu_gen.py (TOKSIM-S81B/FGU): the frame's full multi-phase L0 field is compiled ONCE
(xs_place.compile_frame: production phase list, every phase legalised, real fixture rows / K 2304 / FP8 shared and FP4
routed ROM images), one xs_place vector per non-empty ffn.down phase (p<k>/ == `xs_place.py gen --phase k`), the swap /
shift mutants of the first routed-expert down phase, and one SEQUENCE vector PER EXPERT (seq_<expert>/: the phases of one
w2 matrix share one x = bf16(swiglu * route_w); a different expert needs a different x, which the frame bench's vector
memory holds once).  No RTL, no compiler change.

    toksim_fdown_frame_gen.py --frame u_f_0L00 --fixtures FIX --die-src DIE --out VEC
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

OP = 'ffn.down'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--frame', default='u_f_0L00')
    p.add_argument('--fixtures', required=True)
    p.add_argument('--die-src', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    import dv_layer_compile as C
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    die = C.Die(C.die_tree(None, a.die_src))
    rec, field = XP.compile_frame(die, a.frame, a.fixtures, XP.XS_OPS['L0'] + XP.BF_OPS['L0'], iters=LX.ITERS)
    ns = argparse.Namespace(fixtures=a.fixtures, frame=a.frame, mutant=None, bf_measure=False)
    phs = [ph for ph in rec['phases'] if ph['op'] == OP and ph['rows'] > 0]
    allp = [ph['phase'] for ph in rec['phases'] if ph['op'] == OP]
    for ph in phs:
        assert ph['calendar'] == 'measured_class' and ph['faults'] == 0, (ph['phase'], ph['calendar'], ph['faults'])
        XP.gen_one(ns, rec, field, ph, out / f'p{ph["phase"]}')
    seqs = {}
    for ph in phs:
        seqs.setdefault(ph['mat'], []).append(ph)
    index = dict(phases=[ph['phase'] for ph in phs], all_phases=allp, rows=[ph['rows'] for ph in phs],
                 mats=[ph['mat'] for ph in phs], fmts=[ph.get('fmt') for ph in phs],
                 calendar=sorted({ph['calendar'] for ph in phs}), faults=sum(ph['faults'] for ph in phs), seqs={})
    for mat, sp in seqs.items():
        d0 = out / f'p{sp[0]["phase"]}'
        m0 = json.loads((d0 / 'meta.json').read_text())
        for ph in sp[1:]:
            mk = json.loads((out / f'p{ph["phase"]}' / 'meta.json').read_text())
            assert mk['images'] == m0['images'], ('field images differ across phases', ph['phase'])
            assert sha(out / f'p{ph["phase"]}' / 'vm.hex') == sha(d0 / 'vm.hex'), ('x differs within one matrix', ph['phase'])
        sd = out / f'seq_{mat.split(".")[0]}'
        if sd.exists():
            shutil.rmtree(sd)
        shutil.copytree(d0, sd)
        (sd / 'meta.json').unlink()
        (sd / 'ARGS').unlink()
        (sd / 'seq.hex').write_text(''.join(f'{(ph["rows"] << 16) | ph["phase"]:08x}\n' for ph in sp))
        (sd / 'seq.json').write_text(json.dumps(dict(op=OP, mat=mat, frame=a.frame, phases=[ph['phase'] for ph in sp],
                                                     rows=[ph['rows'] for ph in sp], K=m0['K'],
                                                     vectors=[f'p{ph["phase"]}' for ph in sp]), indent=1) + '\n')
        index['seqs'][mat] = dict(dir=sd.name, phases=[ph['phase'] for ph in sp], rows=[ph['rows'] for ph in sp], K=m0['K'])
    k0 = next(ph for ph in phs if not ph['mat'].startswith('shared'))
    for m in ('swap', 'shift'):
        XP.gen_one(argparse.Namespace(fixtures=a.fixtures, frame=a.frame, mutant=m, bf_measure=False), rec, field, k0,
                   out / f'm_{m}_p{k0["phase"]}')
    (out / 'index.json').write_text(json.dumps(dict(frame=a.frame, master=rec['master'], lk=rec['lk'],
                                                    slice=rec['slice'], frame_index=rec['frame_index'],
                                                    nphases=rec['nphases'], pairs=rec['pairs'], ops={OP: index},
                                                    fixture_meta_sha256=sha(Path(a.fixtures) / 'meta.json')),
                                               indent=1) + '\n')
    print('TOKSIM_FDOWN_GEN', a.frame, json.dumps({m: (v['phases'], v['rows'], v['K']) for m, v in index['seqs'].items()}))


if __name__ == '__main__':
    main()
