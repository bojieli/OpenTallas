#!/usr/bin/env python3
"""QW-XHEAD XT1 prep (fleet, ot-epyc5 data): real TP8 rank-0 L0 code-ROM masks for the 16 tiles of ONE cluster, the
ROM-layout precheck against the QW-REALSTG matvec fixtures, and the golden level-6 cluster words.

  xt1_prep.py --img DIR(L0/die0) --fx DIR(qw-realstg/fx) --cid 1 --out DIR [--swap A,B]

ROM masks: the transform of tools/qwen_code_rom/build.py (physical() + readback()), bank b of tile t = resident words
4096 b .. 4096 b + 4095, column c = code bytes 32 c .. 32 c + 31 of the tile's 64 (groups 4 t .. 4 t + 3).  Only the L0
words are populated (resident base 0, the stage-1 relocation base): rows 512 .. 4095 of bank 0 and banks 1 .. 4 are ZERO
here (layers 1 .. 35 + head on the real die; never read by a stage-1 op).  --swap A,B writes tile A's masks under B's
name and B's under A's (mutant: wrong ROM binding).

Layout precheck (the claim the tile computes on these bytes): code byte (word a, group g, lane l) == W[row, col] of the
fixture matrix with a = wbase + r ts + k ks + j js, row = 128 (blocks-per-round r + g div S) + 16 j + l, col = kc (g mod S)
+ k  (ib fields of the tt_ctlm ROM command, ibdec.py), for every group of the cluster and every op.
Golden: rtl/test/qwen_dv/dv_bench.l6_parts (hdc_golden matvec chunk sums, pairwise tree over 64 chunks) on the fixture
int8 rows x the fixture x, part index = the cluster's chunk block.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dv_bench as B          # noqa: E402

G, F = B.G, B.F
WORD_BYTES, GT = 49152, 3072
REV = 'b968826d9c46dd6066d109eabc6255188de91218'
LOCK = '5cd6273118054c4a9140682bcd7a32488d8697db26bedf5d7ece8de99e141607'
# ROM command fields of the L0 stage-1 ops (tt_ctlm_prog unit_c4 log, stage 1, decoded by ibdec.dec380)
OPS = dict(
    qkv=dict(pc=1, nout=768, tiles=1, k=8, wbase=0, ts=64, ks=8, js=1, split=9, xbase=4096, xcs=8, xks=1),
    o=dict(pc=12, nout=4096, tiles=3, k=2, wbase=64, ts=16, ks=8, js=1, split=8, xbase=50672, xcs=2, xks=1),
    gu=dict(pc=16, nout=3072, tiles=1, k=32, wbase=112, ts=256, ks=8, js=1, split=7, xbase=4096, xcs=32, xks=1),
    down=dict(pc=20, nout=4096, tiles=3, k=6, wbase=368, ts=48, ks=8, js=1, split=8, xbase=55280, xcs=6, xks=1),
)


def physical(words):
    bits = np.unpackbits(words, axis=1, bitorder='little').reshape(512, 8, 256)
    bitlines = np.packbits(bits.transpose(0, 2, 1), axis=2, bitorder='little').reshape(512, 256)
    return np.concatenate((bitlines, np.zeros((512, 10), dtype=np.uint8)), axis=1)


def readback(mask, expected):
    bits = np.unpackbits(mask[:, :256], axis=1, bitorder='little').reshape(512, 256, 8)
    words = np.packbits(bits.transpose(0, 2, 1), axis=2, bitorder='little').reshape(4096, 32)
    if not np.array_equal(words, expected) or np.any(mask[:, 256:]):
        raise ValueError('physical mask decoder disagrees with the code bytes')


def load_words(img):
    meta = json.loads((img / 'layer0_rom.json').read_text())
    ident = (meta['tp'], meta['die'], meta['layer'], meta['checkpoint_revision'], meta['checkpoint_lock_sha256'])
    if ident != (8, 0, 0, REV, LOCK):
        raise SystemExit(f'wrong source identity {ident}')
    path = img / 'matrix_int8.hex'
    words, h = [], hashlib.sha256()
    with path.open('rb') as f:
        for line in f:
            h.update(line)
            t = line.strip()
            if len(t) != 2 * WORD_BYTES:
                raise SystemExit('bad word width')
            words.append(np.frombuffer(bytes.fromhex(t.decode())[::-1], dtype=np.uint8))
    if len(words) != 512 or h.hexdigest() != meta['image_sha256']['matrix_int8.hex']:
        raise SystemExit('image pin mismatch')
    return np.stack(words), dict(path=str(path), sha256=h.hexdigest(), meta=str(img / 'layer0_rom.json'))


def fixture(fx, name):
    if name in ('qkv', 'gu'):
        z = np.load(fx / f'L0_mat_{name}.npz')
        return z['w'].astype(np.int64), z['x'].astype(F)
    z = np.load(fx / 'L0_mat_od.npz')
    return z[f'{name}_w'].astype(np.int64), z[f'{name}_x'].astype(F)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--img', required=True)
    ap.add_argument('--fx', required=True)
    ap.add_argument('--cid', type=int, default=1)
    ap.add_argument('--out', required=True)
    ap.add_argument('--swap', default='')
    a = ap.parse_args()
    out = Path(a.out); (out / 'masks').mkdir(parents=True, exist_ok=True)
    words, src = load_words(Path(a.img))
    tiles = list(range(16 * a.cid, 16 * a.cid + 16))
    name_of = {t: t for t in tiles}
    if a.swap:
        x, y = (int(v) for v in a.swap.split(','))
        name_of[x], name_of[y] = y, x
    zero = np.zeros((4096, 32), dtype=np.uint8)
    zmask = physical(zero)
    rec = dict(source=src, cid=a.cid, tiles=tiles, swap=a.swap, masks={},
               note='bank 0 rows 0..511 = L0 words (resident base 0 = stage 1); bank 0 rows 512..4095 and banks 1..4 '
                    'ZERO (layers 1..35 / head on the die, not read by stage-1 ops)')
    for t in tiles:
        for b in range(5):
            for c in range(2):
                if b == 0:
                    data = np.zeros((4096, 32), dtype=np.uint8)
                    data[:512] = words[:, 64 * t + 32 * c: 64 * t + 32 * c + 32]
                    m = physical(data); readback(m, data)
                else:
                    m = zmask
                p = out / 'masks' / f'qtile_t{name_of[t]}_b{b}_c{c}.viamap.hex'
                txt = ''.join(row[::-1].tobytes().hex() + '\n' for row in m)
                p.write_text(txt)
                rec['masks'][p.name] = hashlib.sha256(txt.encode()).hexdigest()
    # layout precheck + golden
    fx = Path(a.fx)
    gold = {}
    for name, op in OPS.items():
        w, x = fixture(fx, name)
        S = 1 << op['split']
        kc = op['k']
        nblk = GT // S                      # 128-row blocks per round
        jw = 8                              # 16-row words per 128-row block
        assert w.shape == (op['nout'], S * kc), (name, w.shape, S, kc)
        bad = 0
        for g in range(64 * a.cid, 64 * a.cid + 64):
            t, i = divmod(g, 4)
            for r in range(op['tiles']):
                for j in range(jw):
                    for k in range(kc):
                        adr = op['wbase'] + r * op['ts'] + k * op['ks'] + j * op['js']
                        rom = words[adr, 16 * g:16 * g + 16].view(np.int8).astype(np.int64)
                        row0 = 128 * (r * nblk + g // S) + 16 * j
                        if row0 >= op['nout']:
                            continue
                        ref = w[row0:row0 + 16, kc * (g % S) + k]
                        bad += int(np.sum(rom != ref))
        parts = B.l6_parts(w.astype(F), x, S)                 # per cluster chunk block, all rows
        cb = (64 * a.cid) % S // 64                            # the cluster's chunk block inside one 128-row block
        nclu = S // 64
        exp = []
        for r in range(op['tiles']):
            blk = r * nblk + (64 * a.cid) // S
            if 128 * blk >= op['nout']:
                continue
            p = parts[cb] if nclu > 0 else None
            for j in range(8):
                v = np.asarray(p, dtype=F)[128 * blk + 16 * j:128 * blk + 16 * j + 16]
                exp.append(dict(round=r, block=blk, j=j, word=f'{B.word16(v):0128x}'))
        # the x stream: 64-element beats covering xbase .. xbase + S kc (BF16 RNE of the fixture x)
        xb = B.G.to_bf16(x)
        xbits = (np.asarray(xb, dtype=F).view(np.uint32) >> 16).astype(np.uint64)
        n = len(xbits)
        lo = op['xbase'] // 64 * 64
        hi = -(-(op['xbase'] + n) // 64) * 64
        beats = []
        for e0 in range(lo, hi, 64):
            vals = [int(xbits[e - op['xbase']]) if op['xbase'] <= e < op['xbase'] + n else 0 for e in range(e0, e0 + 64)]
            beats.append(dict(eaddr=e0, payload=f'{sum(v << (16 * q) for q, v in enumerate(vals)):0256x}'))
        gold[name] = dict(op=op, layout_mismatch_bytes=bad, words=exp, x_beats=beats, cluster_chunk_block=cb,
                          blocks_per_round=nblk, j_words=jw)
        print(f'{name}: S {S} kc {kc} rounds {op["tiles"]} layout mismatches {bad} words {len(exp)} beats {len(beats)}')
    (out / 'gold.json').write_text(json.dumps(gold))
    (out / 'prep.json').write_text(json.dumps(rec, indent=1))
    print('PREP DONE')


if __name__ == '__main__':
    main()
