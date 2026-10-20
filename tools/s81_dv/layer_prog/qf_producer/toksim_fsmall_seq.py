#!/usr/bin/env python3
"""TOKSIM-S81B/FSMALL (10-19): one phase-sequence vector of an op from the per-phase vectors of toksim_fsmall_gen.py (same
construction as toksim_fgu_gen.py: the field images are the whole multi-phase field, identical in every phase dir; seq.hex =
{rows, phase} per phase in field order) for tb_toksim_fgu_seq.sv + toksim_fgu_check.py seq.
    toksim_fsmall_seq.py --vec VEC/<layer>/<frame> --op attn.idx.q   -> VEC/.../seq_<op tail>/ ; prints SEQ dir n K ops"""
import argparse, hashlib, json, shutil, sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--vec', required=True); p.add_argument('--op', required=True)
    a = p.parse_args(); v = Path(a.vec)
    fr = json.loads((v / 'frame.json').read_text())
    phs = [x for x in fr['phases'] if x['op'] == a.op and x['rows'] > 0]
    if len(phs) < 2:
        print('SEQ_NONE', len(phs)); return 0
    d0 = v / f'p{phs[0]["phase"]}'; m0 = json.loads((d0 / 'meta.json').read_text())
    for ph in phs[1:]:
        mk = json.loads((v / f'p{ph["phase"]}' / 'meta.json').read_text())
        assert mk['images'] == m0['images'], ('field images differ', ph['phase'])
        assert sha(v / f'p{ph["phase"]}' / 'vm.hex') == sha(d0 / 'vm.hex'), ('x differs', ph['phase'])
    sd = v / f'seq_{a.op.split(".", 1)[1].replace(".", "_")}'
    if sd.exists():
        shutil.rmtree(sd)
    shutil.copytree(d0, sd); (sd / 'meta.json').unlink(); (sd / 'ARGS').unlink()
    (sd / 'seq.hex').write_text(''.join(f'{(ph["rows"] << 16) | ph["phase"]:08x}\n' for ph in phs))
    (sd / 'seq.json').write_text(json.dumps(dict(op=a.op, frame=fr['frame'], phases=[ph['phase'] for ph in phs],
        rows=[ph['rows'] for ph in phs], K=m0['K'], vectors=[f'p{ph["phase"]}' for ph in phs]), indent=1) + '\n')
    print('SEQ', sd, len(phs), m0['K'], max(ph['rows'] for ph in phs), phs[0]['phase'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
