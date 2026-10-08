#!/usr/bin/env python3
"""Parent-boundary fixture for the integrated minimum parent norm stage.

Golden: tools/hdc_golden_v41 (the release model the parent's ot_dsrom_su_norm
is specified against): KIND0 y = rmsnorm_bf16(hc_pre(x, pre), w, eps), KIND1
y = rmsnorm_bf16(x, w, eps). The model is checked first against the retained
DS1M stage (5120/5120 equal to its golden ey.mem); a fixture is written only if
that check passes. Provider images use the NS2 address map of
prepare_integrated_minimum_parent_fixture.py (x at word 0, gain at XW).
--corrupt-word N also writes gold_corrupt/ with ey word N's bit 16 flipped
(negative control: the harness must report a golden mismatch at that word).
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import hdc_golden_v41 as G

def u32(p): return np.array([int(s, 16) for s in Path(p).read_text().split()], dtype=np.uint32)
def write(p, a): Path(p).write_text(''.join(f'{int(v):08x}\n' for v in a))
def golden(kind, x, w, cfg):
    f = cfg.view(np.float32)
    if kind == 0:
        X = x.view(np.float32).reshape(4, -1)
        h = G.to_bf16(G.seqsum([G.mul(np.float32(f[j]), X[j]) for j in range(4)]))
    else:
        h = x.view(np.float32)
    assert float(f[4]) == len(w), 'n_f must equal D'
    return np.asarray(G.rmsnorm_bf16(h, w.view(np.float32), f[5]), dtype=np.float32).view(np.uint32)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ds-retained', type=Path, required=True, help='retained DS1M gold dir (model self-check)')
    ap.add_argument('--kind', type=int, choices=[0, 1], required=True)
    ap.add_argument('--x', type=Path, required=True); ap.add_argument('--w', type=Path, required=True)
    ap.add_argument('--eps-hex', required=True); ap.add_argument('--pre-hex', default='0,0,0,0')
    ap.add_argument('--position', type=lambda s: int(s, 0), required=True)
    ap.add_argument('--provenance', required=True); ap.add_argument('--corrupt-word', type=int)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    r = a.ds_retained
    ds = golden(0, u32(r/'x.mem'), u32(r/'w.mem'), u32(r/'cfg.mem'))
    eq = int((ds == u32(r/'ey.mem')).sum())
    if eq != 5120: raise SystemExit(f'golden model self-check FAIL on DS1M retained stage: {eq}/5120')
    x, w = u32(a.x), u32(a.w); D = len(w)
    if len(x) != (4 if a.kind == 0 else 1)*D: raise SystemExit('x/gain shape')
    cfg = np.array([int(v, 16) for v in a.pre_hex.split(',')] +
                   [np.float32(D).view(np.uint32), int(a.eps_hex, 16)], dtype=np.uint32)
    ey = golden(a.kind, x, w, cfg)
    o = a.output; o.mkdir(parents=True, exist_ok=False); (o/'gold').mkdir()
    for n, v in (('x.mem', x), ('w.mem', w), ('cfg.mem', cfg), ('ey.mem', ey)): write(o/'gold'/n, v)
    if a.corrupt_word is not None:
        (o/'gold_corrupt').mkdir(); bad = ey.copy(); bad[a.corrupt_word] ^= 1 << 16
        for n, v in (('x.mem', x), ('w.mem', w), ('cfg.mem', cfg), ('ey.mem', bad)): write(o/'gold_corrupt'/n, v)
    rows = [{}, {}]
    for word, value in enumerate(np.concatenate([x, w]).tolist()):
        address = word*4; si = (address >> 7) & 1; local = ((address >> 8) << 7) | (address & 127)
        rows[si][local >> 5] = rows[si].get(local >> 5, 0) | (int(value) << ((address & 31)*8))
    for die in range(2):
        for part in range(2):
            img = rows[part] if die == 0 else {0: 0}
            with (o/f'die{die}_p{part}.hex').open('x') as f:
                for sec, val in sorted(img.items()): f.write(f'@{sec:x}\n{val:064x}\n')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    (o/'fixture_manifest.json').write_text(json.dumps(dict(
        kind=a.kind, D=D, position=a.position, provenance=a.provenance,
        golden='tools/hdc_golden_v41 rmsnorm_bf16' + (' over hc_pre' if a.kind == 0 else ''),
        golden_model_selfcheck_ds1m='5120/5120', corrupt_word=a.corrupt_word,
        files={str(p.relative_to(o)): sha(p) for p in sorted(o.rglob('*')) if p.is_file()}), indent=2)+'\n')
    print('fixture', o, 'D', D, 'ey[0:2]', [f'{v:08x}' for v in ey[:2]])

if __name__ == '__main__':
    main()
