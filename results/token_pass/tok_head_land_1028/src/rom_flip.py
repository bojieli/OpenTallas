#!/usr/bin/env python3
"""TOK-HEAD-LAND-1 mutant ROMFLIP: tE3b4 (rank-0 argmax tile, row0 21888) images with ONE weight word changed.
Row 21946 (local 58 -> ha1 row 26) dim K = argmax |x| in 0..4095: BF16 bit 14 flipped (exponent MSB) in the released
head.weight copy, images rewritten with the same head_native_fullweight._gen_one path (SK 11).  Output: a full img dir
(symlinks to the nominal rank-0 tiles) with tE3b4 replaced; the diff vs nominal must be exactly ONE ROM word."""
import os, sys, shutil, filecmp
from pathlib import Path
import numpy as np
W = Path(sys.argv[1]); NOM = Path(sys.argv[2]); OUT = Path(sys.argv[3])
sys.path.insert(0, str(W / 'tools')); sys.path.insert(0, str(W / 'tools/s81_head'))
import dsrom_1m_head as H
H.SK = 11
H.setup_gate()
xf, logits = H.golden_x()
ck = H.Ckpt(H.SNAP)
dt, sh, buf = ck.raw('head.weight')
full = np.frombuffer(buf, dtype=np.uint16).reshape(sh)
row0 = 21888
u = full[row0:row0 + 128].astype(np.uint64).copy()
x16 = (H.G.bits(xf).astype(np.uint32) >> 16)
k = int(np.argmax(np.abs(np.asarray(xf[:4096], dtype=np.float32))))
before = int(u[58, k]); u[58, k] ^= np.uint64(1 << 14)
print('flip row', row0 + 58, 'dim', k, 'x', float(xf[k]), 'w %04x -> %04x' % (before, int(u[58, k])))
OUT.mkdir(parents=True, exist_ok=False)
for e in NOM.iterdir():
    if e.name != 'tE3b4':
        os.symlink(e.resolve(), OUT / e.name)
t = OUT / 'tE3b4'; t.mkdir()
for q in range(4):
    H.write_macro(H.skewed_image(u[32 * q:32 * q + 32, :4096].reshape(H.NW, 16)), t, f'ha{q}')
perm = np.array([32 * (n % 4) + n // 4 for n in range(128)])
H.write_macro(H.skewed_image(u[perm, 4096:].reshape(H.NW, 16)), t, 'hb')
for f in ('xa.hex', 'xb.hex'):
    os.symlink((NOM / f).resolve(), t / f)
nd = 0
for f in sorted((NOM / 'tE3b4').iterdir()):
    if f.name in ('xa.hex', 'xb.hex'):
        continue
    a = f.read_text().split('\n'); b = (t / f.name).read_text().split('\n')
    d = [i for i, (p, q) in enumerate(zip(a, b)) if p != q]
    if d or len(a) != len(b):
        print('DIFF', f.name, 'lines', d[:5], 'len', len(a), len(b)); nd += len(d)
print('ROM_WORDS_CHANGED', nd)
