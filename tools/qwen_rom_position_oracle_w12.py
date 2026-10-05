#!/usr/bin/env python3
"""ISA golden for a Qwen3-8B O4 ROM TP4 token at a NONZERO position, with a populated KV cache.

The retained TP4 oracle (tools/qwen_o4_token_oracle_w12.py) covers token 0 at
position 0 with a zero KV window.  This tool runs the same ISA machines
(tools/qwen_o4_layer0_oracle_w12.py DieMachine: dense matrices by the golden
contiguous K-split reduction, attention and stream instructions by the ISA
golden in tools/hdc_program.py / tools/hdc_golden.py, TP all-reduce by the
golden fold in descriptor order) over a prompt, one position at a time:

  for p in 0 .. P:   X = embedding(token[p]) at VM element 4096, the rest of VM zero
                     (exactly the runtime's fresh VM), then layers 0 .. N-1 with
                     dyn_values(token[p], p) and each layer's persistent KV window.

Positions 0 .. P-1 are the golden PREFILL (sequential decode): they populate
each layer's KV window exactly as the ISA writes it (FP8 E4M3 values held as
FP32).  Position P is the decode token under test.  Written per layer and die:

  kv_pre/L<n>_die<d>.npy    the KV window BEFORE position P (uint32 FP32 bits, the
                            runtime's element layout, 2 * kv_v0 elements)
  kv_at_P/L<n>_die<d>.json  the K and V elements the token at P writes (checks the
                            RTL write path)
  L<nn>_die<d>_x.hex        X after layer n at position P (the RTL comparison)
  x_preload.hex             X(token[P]) in the runtime's @1000 preload format

Embedding rows are the shipped INT8 codes times their BF16 row scale
(tools/hdc_qwen_int8_image.shipped_vocab_rows; exact in FP32, as
rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv computes them).

Not an RTL verdict.  Run with QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024
HDC_KV_FMT=fp8 (the retained oracle's arithmetic environment).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as QI
import hdc_qwen_fullshape_program_w12 as FP
import qwen_o4_layer0_oracle_w12 as L0

ROOT = Path(__file__).resolve().parents[1]
W, TP, GROUPS = L0.W, L0.TP, L0.GROUPS
VM = L0.VM
X_BASE = VM['X']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class StageImage(L0.Image):
    """A layer image (any layer) consumed by its own image digests.

    The emitter-source check of L0.Image is not repeated: these are the retained
    TP4 stage images, pinned by their image_sha256 (and by the retained run's
    stage_image_sha256); the emitter sources have moved on main since.  Decoded
    matrices are memoised (the base class re-reads the 200 MB hex per call).
    """

    def __init__(self, directory, layer):
        self.dir = Path(directory)
        self.manifest = json.loads((self.dir / f'layer{layer}_rom.json').read_text())
        if self.manifest['layer'] != layer or self.manifest['tp'] != TP:
            raise ValueError(f'expected layer {layer} TP{TP} images in {directory}')
        self.image_sha = {}
        for name, digest in self.manifest['image_sha256'].items():
            got = sha(self.dir / name)   # the retained images, consumed by digest
            if got != digest:
                raise ValueError(f'image digest mismatch: {directory}/{name}')
            self.image_sha[name] = got
        self.layout = {row['base']: row for row in self.manifest['matrix_layout']}
        self.program = [QI.decode_instruction(int(line, 16)) for line in (self.dir / 'program.hex').read_text().split()]
        self.descriptors = [QI.decode_descriptor(int(line, 16)) for line in (self.dir / 'segments.hex').read_text().split()]
        lo, hi = [], []
        with (self.dir / 'crom.hex').open() as stream:
            for line in stream:
                line = line.strip()
                if not line or line.startswith('@'):
                    continue
                line = line.rjust(16, '0')
                hi.append(int(line[:8], 16))
                lo.append(int(line[8:16], 16))
        self.crom = np.stack((G.from_bits(np.array(lo, dtype=np.uint32)),
                              G.from_bits(np.array(hi, dtype=np.uint32))), axis=1)
        self._mat = {}

    def matrix(self, meta):
        key = meta['base']
        if key not in self._mat:
            self._mat[key] = super().matrix(meta)
        return self._mat[key]


def matvec_chunked(wT, x, split):
    """G.matvec(w, x, split) with the identical per-element operation order, vectorised over
    the split chunks: wT[k, c, n] = w[n, c*kc + k].  Each chunk accumulates its kc products
    sequentially from +0 (G.add/G.mul, z-canonicalised), then the chunk sums are added by the
    same pairwise tree ((c0+c1)+(c2+c3)).  Rows and chunks are independent, so the result is
    bit-identical to G.matvec (checked against the retained oracle at position 0)."""
    xb = G.to_bf16(x)
    kc = wT.shape[0]
    xr = xb.reshape(split, kc)
    acc = np.zeros(wT.shape[1:], dtype=np.float32)
    for k in range(kc):
        acc = G.add(acc, G.mul(wT[k], xr[:, k][:, None]))
    while acc.shape[0] > 1:
        acc = G.add(acc[0::2], acc[1::2])
    return acc[0]


class FastDieMachine(L0.DieMachine):
    """L0.DieMachine with the dense matrices evaluated by matvec_chunked (same order)."""

    _wt = {}

    def me(self, f, dyn):
        if f['me_wsrc']:
            return P.Machine.me(self, f, dyn)
        meta = self.image.layout[f['me_wbase']]
        n = f['me_nout'] + dyn[f['me_d_nout']]
        split = 1 << f['me_split']
        if n != meta['rows'] or split != meta['split']:
            raise ValueError(f'ISA/matrix geometry mismatch: {meta["name"]}')
        key = (id(self.image), meta['base'])
        if key not in self._wt:
            codes, scales = self.image.matrix(meta)
            k = meta['columns']
            kc = k // split
            wT = np.ascontiguousarray(codes.astype(np.float32).reshape(n, split, kc).transpose(2, 1, 0))
            self._wt[key] = (wT, scales)
        wT, scales = self._wt[key]
        xbase = f['me_xbase'] + dyn[f['me_d_xbase']]
        x = self.vm[xbase:xbase + meta['columns']]
        raw = matvec_chunked(wT, x, split)
        out = raw if meta['name'] in ('o', 'down') else G.mul(raw, scales)
        if not f['me_oen']:
            raise ValueError('layer oracle expects each matrix to write VM')
        self.vm[f['me_obase'] * W:f['me_obase'] * W + n] = out


def embedding_x(snapshot, tokens):
    """FP32 X rows: shipped INT8 code x BF16 row scale (exact)."""
    from hdc_qwen_int8_image import shipped_vocab_rows
    out = {}
    for t in sorted(set(tokens)):
        rows = shipped_vocab_rows(snapshot, 'embedding', start=int(t), count=1)
        codes = rows['codes'].numpy().reshape(-1).astype(np.int8)
        sbits = rows['scales'].view(__import__('torch').int16).numpy().view(np.uint16).reshape(-1)
        scale = G.from_bits(np.uint32(sbits[0]) << np.uint32(16))
        x = (codes.astype(np.float32) * np.float32(scale)).astype(np.float32)
        if len(x) != 4096:
            raise ValueError('embedding row width')
        out[int(t)] = (x, int(sbits[0]), codes.view(np.uint8).copy())
    return out


def run_layer(images, machines, vms, token, pos):
    for mach, vm in zip(machines, vms):
        mach.vm[:] = vm
        mach.pos = pos
    with FP.program_geometry(VM):
        dyns = [P.dyn_values(m.lay, token=token, pos=pos) for m in machines]
        desc = images[0].descriptors
        for idx, seg in enumerate(desc):
            first = seg['program_base']
            end = desc[idx + 1]['program_base'] if idx + 1 < len(desc) else len(images[0].program)
            for mach, image, dyn in zip(machines, images, dyns):
                for pc in range(first, end):
                    f = image.program[pc]
                    if f['unit'] == I.UNIT_ME:
                        mach.me(f, dyn)
                    elif f['unit'] == I.UNIT_SU:
                        mach.su(f, dyn)
            if seg['kind'] == P.COLL_ALLREDUCE:
                lo, hi = seg['vm_word'] * W, (seg['vm_word'] + seg['words']) * W
                summed = G.fold([m.vm[lo:hi].copy() for m in machines])
                for mach in machines:
                    mach.vm[lo:hi] = summed
            elif seg['kind'] != P.COLL_END:
                raise ValueError('unexpected layer collective')
    return [m.vm.copy() for m in machines]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--layer-dirs', required=True, help='format string with {layer} and {die} (retained TP4 images)')
    ap.add_argument('--layers', type=int, required=True, help='decoder layers 0 .. N-1')
    ap.add_argument('--tokens', type=Path, required=True, help='whitespace-separated prompt token ids')
    ap.add_argument('--positions', required=True, help='comma-separated decode positions to record (the last is run to)')
    ap.add_argument('--snapshot', type=Path, help='pinned Qwen3-8B snapshot (embedding rows)')
    ap.add_argument('--embedding-npz', type=Path, help='rows exported by --export-embedding from the snapshot (hosts without torch)')
    ap.add_argument('--export-embedding', type=Path, help='write the prompt rows (codes, scales) to this npz and exit')
    ap.add_argument('--check-token0-preload', type=Path, help='vm_x_fp32.hex of token 0: must equal our embedding')
    ap.add_argument('--reference-dense', action='store_true',
                    help='evaluate dense matrices with the unvectorised L0.DieMachine (equivalence check)')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if I.SU_WIDTH != 1024 or G.SU_WIDTH != 1024 or G.KV_FMT != 'fp8' or GROUPS != 6144 or TP != 4:
        raise SystemExit('requires QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8')
    tokens = [int(t) for t in args.tokens.read_text().split()]
    rec_pos = sorted(int(p) for p in args.positions.split(','))
    last = rec_pos[-1]
    if last >= len(tokens) or last >= FP.TMAX:
        raise SystemExit('position beyond the prompt or the KV window')
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    need = tokens[:last + 1] + ([0] if args.check_token0_preload else [])
    if args.embedding_npz:
        z = np.load(args.embedding_npz)
        emb = {}
        for t, sc, cd in zip(z['tokens'], z['scales'], z['codes']):
            x = (cd.view(np.int8).astype(np.float32) * np.float32(G.from_bits(np.uint32(sc) << np.uint32(16)))).astype(np.float32)
            emb[int(t)] = (x, int(sc), cd.copy())
        missing = set(need) - set(emb)
        if missing:
            raise SystemExit(f'embedding npz lacks tokens {sorted(missing)[:5]}')
        record_emb = {'embedding_npz_sha256': sha(args.embedding_npz)}
    else:
        emb = embedding_x(args.snapshot, need)
        record_emb = {}
    if args.export_embedding:
        ts = sorted(emb)
        np.savez(args.export_embedding, tokens=np.array(ts, dtype=np.int64),
                 scales=np.array([emb[t][1] for t in ts], dtype=np.uint16),
                 codes=np.stack([emb[t][2] for t in ts]))
        print('exported', len(ts), 'rows')
        return
    record = {'schema': 'opentallas.qwen-rom-tp4-position-oracle.v1', 'status': 'ISA_golden_only',
              'layers': args.layers, 'tp': TP, 'groups': GROUPS, 'su_width_arith': G.SU_WIDTH,
              'kv_format': G.KV_FMT, 'tokens_sha256': sha(args.tokens), 'tokens_used': tokens[:last + 1],
              'positions': rec_pos, 'layer_image_sha256': {}, 'per_position': {},
              'dense_kernel': 'reference' if args.reference_dense else 'vectorised_same_order',
              'oracle_source_sha256': {p: sha(ROOT / p) for p in (
                  'tools/qwen_rom_position_oracle_w12.py', 'tools/qwen_o4_layer0_oracle_w12.py',
                  'tools/hdc_golden.py', 'tools/hdc_program.py', 'tools/hdc_isa.py',
                  'tools/hdc_qwen_fullshape_isa_w12.py', 'tools/hdc_qwen_fullshape_program_w12.py',
                  'tools/hdc_qwen_int8_image.py')},
              'claim_boundary': 'ISA golden over a real prompt: positions < P are the golden prefill '
                                '(sequential decode), position P the token under test. Not an RTL verdict.'}
    record.update(record_emb)
    if args.check_token0_preload:
        x0 = L0._preload_x(args.check_token0_preload)
        ok = bool(np.array_equal(G.bits(x0), G.bits(emb[0][0])))
        record['token0_embedding_equals_retained_preload'] = ok
        if not ok:
            raise SystemExit('embedding decode does not reproduce the retained token-0 preload')
    images = [[StageImage(args.layer_dirs.format(layer=n, die=d), n) for d in range(TP)] for n in range(args.layers)]
    for n, ims in enumerate(images):
        if any(im.descriptors != ims[0].descriptors for im in ims):
            raise ValueError('TP descriptor mismatch')
        record['layer_image_sha256'][f'L{n}'] = [im.image_sha for im in ims]
    machine = L0.DieMachine if args.reference_dense else FastDieMachine
    machines = [[machine(im) for im in ims] for ims in images]
    for p in range(last + 1):
        tok = tokens[p]
        x = emb[tok][0]
        vms = []
        for d in range(TP):
            vm = np.zeros(L0.VM_ELEMS, dtype=np.float32)
            vm[X_BASE:X_BASE + 4096] = x
            vms.append(vm)
        recording = p in rec_pos
        if recording:
            pdir = out / f'P{p}'
            (pdir / 'kv_pre').mkdir(parents=True, exist_ok=True)
            (pdir / 'kv_at_P').mkdir(parents=True, exist_ok=True)
            L0._bits_hex(pdir / 'x_preload_body.hex', x)
            (pdir / 'x_preload.hex').write_text('@1000\n' + (pdir / 'x_preload_body.hex').read_text())
            (pdir / 'x_preload_body.hex').unlink()
            (pdir / 'embedding_row.json').write_text(json.dumps(
                {'token': tok, 'scale_bf16': f'{emb[tok][1]:04x}', 'codes_hex': emb[tok][2].tobytes().hex()}) + '\n')
            prec = {'token': tok, 'x_preload_sha256': sha(pdir / 'x_preload.hex'), 'layer_x_sha256': {},
                    'kv_pre_sha256': {}, 'kv_at_P_sha256': {}}
        for n in range(args.layers):
            if recording:
                for d in range(TP):
                    path = pdir / 'kv_pre' / f'L{n}_die{d}.npy'
                    np.save(path, G.bits(machines[n][d].kv).astype(np.uint32))
                    prec['kv_pre_sha256'][f'L{n}_die{d}'] = sha(path)
            vms = run_layer(images[n], machines[n], vms, tok, p)
            if recording:
                for d in range(TP):
                    lay = machines[n][d].lay
                    kv = machines[n][d].kv
                    kel = [lay.k_elem(0, h, p, dim) for h in range(lay.KV) for dim in range(lay.HD)]
                    vel = [lay.v_elem(0, h, p, dim) for h in range(lay.KV) for dim in range(lay.HD)]
                    path = pdir / 'kv_at_P' / f'L{n}_die{d}.json'
                    path.write_text(json.dumps({'k_elem': kel, 'k_bits': [f'{int(b):08x}' for b in G.bits(kv[kel])],
                                                'v_elem': vel, 'v_bits': [f'{int(b):08x}' for b in G.bits(kv[vel])]}) + '\n')
                    prec['kv_at_P_sha256'][f'L{n}_die{d}'] = sha(path)
                    xpath = pdir / f'L{n:02d}_die{d}_x.hex'
                    L0._bits_hex(xpath, vms[d][X_BASE:X_BASE + 4096])
                    prec['layer_x_sha256'][f'L{n}_die{d}'] = sha(xpath)
        if recording:
            record['per_position'][str(p)] = prec
            (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        if p % 16 == 0 or recording:
            print(f'position {p} done ({time.time() - t0:.0f} s)', flush=True)
    record['wall_seconds'] = round(time.time() - t0, 1)
    (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'positions': rec_pos, 'wall_seconds': record['wall_seconds']}))


if __name__ == '__main__':
    main()
