#!/usr/bin/env python3
"""TOKSIM-S81B/FGU (10-19): frame vectors for EVERY ffn.experts_gu / ffn.shared_gu phase of one die frame.

Compiles the frame's full multi-phase field ONCE (xs_place.compile_frame: production phase list of L0, every phase
legalised, real fixture rows / K / ROM images), then writes one xs_place vector per non-empty target phase (p<k>/,
identical to `xs_place.py gen --phase k`), the swap / shift mutants of the first experts_gu phase, and one SEQUENCE
vector per op (seq_<op>/: the shared field images + seq.hex = {ops, ph} per phase, in field-phase order) for the
phase-sequence bench tb_toksim_fgu_seq.sv.  No RTL, no compiler change.

    toksim_fgu_gen.py --frame u_f_0L00 --fixtures FIX --die-src DIE --out VEC
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

TARGETS = ('ffn.experts_gu', 'ffn.shared_gu')


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
    index = {}
    for op in TARGETS:
        phs = [ph for ph in rec['phases'] if ph['op'] == op and ph['rows'] > 0]
        allp = [ph for ph in rec['phases'] if ph['op'] == op]
        index[op] = dict(phases=[ph['phase'] for ph in phs], all_phases=[ph['phase'] for ph in allp],
                         rows=[ph['rows'] for ph in phs], mats=[ph['mat'] for ph in phs],
                         calendar=sorted({ph['calendar'] for ph in phs}), faults=sum(ph['faults'] for ph in phs))
        for ph in phs:
            assert ph['calendar'] == 'measured_class' and ph['faults'] == 0, (op, ph['phase'], ph['calendar'], ph['faults'])
            XP.gen_one(ns, rec, field, ph, out / f'p{ph["phase"]}')
        # one sequence vector: the field images are the whole multi-phase field, identical in every phase dir
        d0 = out / f'p{phs[0]["phase"]}'
        m0 = json.loads((d0 / 'meta.json').read_text())
        for ph in phs[1:]:
            mk = json.loads((out / f'p{ph["phase"]}' / 'meta.json').read_text())
            assert mk['images'] == m0['images'], ('field images differ across phases', ph['phase'])
            assert sha(out / f'p{ph["phase"]}' / 'vm.hex') == sha(d0 / 'vm.hex'), ('x differs across phases', ph['phase'])
        sd = out / f'seq_{op.split(".")[1]}'
        if sd.exists():
            shutil.rmtree(sd)
        shutil.copytree(d0, sd)
        (sd / 'meta.json').unlink()
        (sd / 'ARGS').unlink()
        (sd / 'seq.hex').write_text(''.join(f'{(ph["rows"] << 16) | ph["phase"]:08x}\n' for ph in phs))
        (sd / 'seq.json').write_text(json.dumps(dict(op=op, frame=a.frame, phases=[ph['phase'] for ph in phs],
                                                     rows=[ph['rows'] for ph in phs], K=m0['K'],
                                                     vectors=[f'p{ph["phase"]}' for ph in phs]), indent=1) + '\n')
    # mutants of the first experts_gu phase (fail witnesses: values swapped between elements / calendar +1)
    k0 = index['ffn.experts_gu']['phases'][0]
    ph0 = next(ph for ph in rec['phases'] if ph['phase'] == k0)
    for m in ('swap', 'shift'):
        XP.gen_one(argparse.Namespace(fixtures=a.fixtures, frame=a.frame, mutant=m, bf_measure=False), rec, field, ph0,
                   out / f'm_{m}_p{k0}')
    (out / 'index.json').write_text(json.dumps(dict(frame=a.frame, master=rec['master'], lk=rec['lk'],
                                                    slice=rec['slice'], frame_index=rec['frame_index'],
                                                    nphases=rec['nphases'], pairs=rec['pairs'], ops=index,
                                                    fixture_meta_sha256=sha(Path(a.fixtures) / 'meta.json')),
                                               indent=1) + '\n')
    print('TOKSIM_FGU_GEN', a.frame, json.dumps({k: (v['phases'], v['rows']) for k, v in index.items()}))


if __name__ == '__main__':
    main()
