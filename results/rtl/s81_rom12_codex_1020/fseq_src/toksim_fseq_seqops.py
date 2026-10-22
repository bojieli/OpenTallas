#!/usr/bin/env python3
"""TOKSIM-S81C/FSEQ (10-19): one phase-sequence vector of SEVERAL ops of a frame, in field order (e.g. attn.wq_b then
attn.idx.q: both read x = attn.q_norm.scale, so the field images and vm.hex are one compile_frame), from the per-phase
vectors of toksim_fsmall_gen.py.  Same construction as toksim_fsmall_seq.py (seq.hex = {rows, phase} per phase) plus
seqw.hex (per phase len(meta.plan.ret), as toksim_fgu_seqw.py) for tb_toksim_fgu_seq +RETIRE=1 / toksim_fgu_check.py seq.
    toksim_fseq_seqops.py --vec VEC/<layer>/<frame> --name NAME --ops attn.wq_b attn.idx.q   -> prints SEQ dir n K ops ph0
--phase-vm: the phases carry DIFFERENT x (BF router: one K segment per phase at the same VM addresses); copy each
phase's vm.hex to SEQ/p<ph>/vm.hex for tb_toksim_fgu_seq +PHASE_VM=1 (reload at each go) instead of asserting one x."""
import argparse, hashlib, json, shutil, sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--vec', required=True); p.add_argument('--name', required=True)
    p.add_argument('--ops', nargs='+', required=True); p.add_argument('--phase-vm', action='store_true')
    a = p.parse_args(); v = Path(a.vec)
    fr = json.loads((v / 'frame.json').read_text())
    phs = sorted([x for x in fr['phases'] if x['op'] in a.ops and x['rows'] > 0], key=lambda x: x['phase'])
    if len(phs) < 2:
        print('SEQ_NONE', len(phs)); return 0
    d0 = v / f'p{phs[0]["phase"]}'; m0 = json.loads((d0 / 'meta.json').read_text())
    for ph in phs[1:]:
        mk = json.loads((v / f'p{ph["phase"]}' / 'meta.json').read_text())
        assert mk['images'] == m0['images'], ('field images differ', ph['phase'])
        assert a.phase_vm or sha(v / f'p{ph["phase"]}' / 'vm.hex') == sha(d0 / 'vm.hex'), ('x differs', ph['phase'])
        assert mk['K'] == m0['K'], ('K differs', ph['phase'])
    sd = v / f'seq_{a.name}'
    if sd.exists():
        shutil.rmtree(sd)
    shutil.copytree(d0, sd); (sd / 'meta.json').unlink(); (sd / 'ARGS').unlink()
    if a.phase_vm:
        for ph in phs:
            (sd / f'p{ph["phase"]}').mkdir(); shutil.copy(v / f'p{ph["phase"]}' / 'vm.hex', sd / f'p{ph["phase"]}' / 'vm.hex')
    (sd / 'seq.hex').write_text(''.join(f'{(ph["rows"] << 16) | ph["phase"]:08x}\n' for ph in phs))
    w = [len(json.loads((v / f'p{ph["phase"]}' / 'meta.json').read_text())['plan']['ret']) for ph in phs]
    (sd / 'seqw.hex').write_text(''.join(f'{x:04x}\n' for x in w))
    (sd / 'seq.json').write_text(json.dumps(dict(op='+'.join(a.ops), frame=fr['frame'], phases=[ph['phase'] for ph in phs],
        ops=[ph['op'] for ph in phs], rows=[ph['rows'] for ph in phs], K=m0['K'], ret_words=w, phase_vm=a.phase_vm,
        vectors=[f'p{ph["phase"]}' for ph in phs]), indent=1) + '\n')
    print('SEQ', sd, len(phs), m0['K'], max(ph['rows'] for ph in phs), phs[0]['phase'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
