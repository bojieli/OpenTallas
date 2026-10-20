#!/usr/bin/env python3
"""TP8 ISA golden for the Qwen3-8B compute-die layer bench (QW-CLAYER-G 10-18): layers 0 .. N-1 over a real prompt.

Why: the current compute die (dv2f14bi; tools/qwen_layerbench/dv_lower.py ownership) is TP8 (qkv 768 rows / die,
o split 256), but fx/realmem/P8191 is the TP4 ISA golden -- a different row / column split and a 4-way AR fold, so it is
not bit-comparable.  This tool is the TP8 equivalent of tools/qwen_rom_position_oracle_w12.py:

  for p in 0 .. P:  X = embedding(token[p]) at VM 'X' of a fresh (zero) VM, then layers 0 .. N-1 (the VM carries
                    between layers, as qwen_tp8_native_layer_oracle --previous-vm does), each layer with its own
                    persistent per-die KV window (written by the programme's own KV SU ops = the golden prefill).

Arithmetic = tools/qwen_tp8_native_layer_oracle.py (NativeOracleMachine: four live Q heads / one KV head, S128 / PV256
attention; dense matrices by tools/qwen_rom_position_oracle_w12.matvec_chunked, bit-identical to G.matvec; collective =
production_tp8_two_level fold ((r0+r4)+(r1+r5))+... as rtl/rom/ot_coll_tp8_die.sv) over the ORIGINAL 29-instruction
checkpoint programme; every visible effect is recorded under its FUSED (25-instruction, actual_fused_layer*) candidate PC
via qwen_tp8_payload_fused_lower.lower_image (QK / exp / PV / reciprocal / normalise = source PCs 11..14 are the fused
native attention, recorded once at source PC 15 = candidate PC 11, as the committed position-255 oracle does).

Only the attention index arrays are precomputed (the reference rebuilds k_elem / v_elem per call: same elements).

Recorded positions write (per layer n, die d):  P<p>/x_preload.hex, embedding_row.json, L<nn>_die<d>_x.hex (X after layer),
kv_pre/L<n>_die<d>.npy, kv_at_P/L<n>_die<d>.json, and at --pc-dump positions die<d>/L<n>/candidate_pc<k>_vm.npz (full VM
bits + defined-effect mask), collective<s>_{partial,return}.hex, ATTN_fp32.hex (the o-proj input), Q_input_fp32.hex,
new_{K,V}_row_fp32.hex, KV commit npz.

Run with QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8 and OT_GOLD_ROOT = a tree whose tools/ hold the
emitter sources pinned by the images' manifests (hdc_qwen_fullshape_isa_w12.py @ 5da3910e4 = add181198a34).  Not an RTL
verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

GROOT = Path(os.environ.get('OT_GOLD_ROOT', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(GROOT / 'tools'))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_program_w12 as FP  # noqa: E402
from hdc_qwen_fullshape_placement_w12 import TP, GROUPS  # noqa: E402
import qwen_rom_position_oracle_w12 as PO  # noqa: E402
from qwen_tp8_payload_fused_lower import lower_image  # noqa: E402

W = I.W_LANES


def production_tp8_fold(partials):
    """= tools/qwen_tp8_native_layer_oracle.production_tp8_fold (copied: that module imports torch): rank = 4*DIE+PKG,
    pair r[p] + r[p+4], then the package fold ((P0+P1)+P2)+P3 (G.fold)."""
    if len(partials) != 8:
        raise ValueError('production TP8 collective requires eight ranks')
    return G.fold([G.add(partials[p], partials[p + 4]) for p in range(4)])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bits_hex(path, values):
    Path(path).write_text(''.join(f'{int(x):08x}\n' for x in G.bits(values)))
    return sha(path)



# ------------------------------------------------------------------ vectorised, bit-identical hdc_golden reductions
# G.matvec_il (the PV product over the context, K up to 8,192) and G.reduce_chunked (every SU sum: softmax
# denominator, norms) loop in Python per element: ~2e9 scalar adds for an 8,192-position prefill.  These are the same
# operations in the same order, vectorised across the independent chunks (a short / empty chunk is padded with +0
# products, which every z-canonical add leaves unchanged).  self_check() compares them with the originals.
_ORIG = {'matvec_il': G.matvec_il, 'reduce_chunked': G.reduce_chunked}


def matvec_il_vec(w, x, split=1):
    w = np.asarray(w, dtype=np.float32)
    x = np.asarray(x, dtype=np.float32)
    n, K = w.shape
    m = -(-K // split)
    if m * split != K:
        w = np.concatenate([w, np.zeros((n, m * split - K), dtype=np.float32)], axis=1)
        x = np.concatenate([x, np.zeros(m * split - K, dtype=np.float32)])
    w3, x2 = w.reshape(n, m, split), x.reshape(m, split)
    acc = np.zeros((n, split), dtype=np.float32)
    for r in range(m):
        acc = G.add(acc, G.mul(w3[:, r, :], x2[r]))
    while acc.shape[1] > 1:
        acc = G.add(acc[:, 0::2], acc[:, 1::2])
    return acc[:, 0]


def reduce_chunked_vec(v, c=G.CHUNK):
    v = np.asarray(v, dtype=np.float32).reshape(-1)
    m = -(-max(len(v), 1) // c)
    v = np.concatenate([v, np.zeros(m * c - len(v), dtype=np.float32)]).reshape(m, c)
    acc = np.zeros(m, dtype=np.float32)
    for j in range(c):
        acc = G.add(acc, v[:, j])
    n = 1
    while n < m:
        n *= 2
    parts = np.concatenate([acc, np.zeros(n - m, dtype=np.float32)])
    while len(parts) > 1:
        parts = G.add(parts[0::2], parts[1::2])
    return np.float32(parts[0])


def self_check(seed=7):
    rng = np.random.default_rng(seed)
    for K, S in ((128, 128), (1, 256), (37, 256), (300, 256), (513, 256), (1000, 8), (64, 1)):
        w = rng.standard_normal((5, K)).astype(np.float32)
        x = rng.standard_normal(K).astype(np.float32)
        w[0, :K // 2] = 0
        x[::7] = -0.0
        a, b = _ORIG['matvec_il'](w, x, S), matvec_il_vec(w, x, S)
        if not np.array_equal(G.bits(a), G.bits(b)):
            raise SystemExit(f'matvec_il_vec differs at K={K} S={S}')
    for L in (0, 1, 7, 8, 9, 64, 129, 1000):
        v = (rng.standard_normal(L) * 1e3).astype(np.float32)
        v[::5] = -0.0
        if G.bits(_ORIG['reduce_chunked'](v)) != G.bits(reduce_chunked_vec(v)):
            raise SystemExit(f'reduce_chunked_vec differs at L={L}')
    G.matvec_il, G.reduce_chunked = matvec_il_vec, reduce_chunked_vec
    return 'PASS (matvec_il 7 shapes, reduce_chunked 8 lengths, signed zeros, vs hdc_golden originals)'


class GoldMachine(PO.FastDieMachine):
    """FastDieMachine (dense) + NativeOracleMachine attention with precomputed element indices."""

    def __init__(self, image, tmax):
        super().__init__(image)
        lay = self.lay
        if lay.NH != 4 or lay.KV != 1 or lay.HD != 128:
            raise ValueError('requires native four-Q/one-KV head ownership')
        self.kidx = np.array([[lay.k_elem(0, 0, t, d) for d in range(128)] for t in range(tmax)], dtype=np.int64)
        self.vidx = np.array([[lay.v_elem(0, 0, t, d) for d in range(128)] for t in range(tmax)], dtype=np.int64)

    def me(self, f, dyn):
        if not f['me_wsrc']:
            return super().me(f, dyn)
        context = self.pos + 1
        if f['me_d_tiles'] == I.DYN_TTILES:
            keys = self.kv[self.kidx[:context]]
            for head in range(4):
                qb = f['me_xbase'] + head * 128
                scores = G.matvec_il(keys, G.to_bf16(self.vm[qb:qb + 128]), 128)
                base = f['me_obase'] * 16 + head * f['me_ojs'] * 16
                self.vm[base:base + context] = scores
                self.vm[f['me_mbase'] + head] = np.max(scores)
        elif f['me_d_k'] == I.DYN_T:
            values = self.kv[self.vidx[:context]]
            for head in range(4):
                eb = f['me_xbase'] + head * f['me_xjs']
                result = G.matvec_il(values.T, G.to_bf16(self.vm[eb:eb + context]), 256)
                base = f['me_obase'] * 16 + head * f['me_ojs'] * 16
                self.vm[base:base + 128] = result
        else:
            raise ValueError('unsupported dynamic attention instruction')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--layer-dirs', required=True, help='format string with {layer} and {die} (TP8 stage images)')
    ap.add_argument('--layers', type=int, required=True)
    ap.add_argument('--tokens', type=Path, required=True)
    ap.add_argument('--embedding-npz', type=Path, required=True, help='prompt rows (tokens, scales, codes)')
    ap.add_argument('--positions', required=True, help='comma-separated positions to record (the last is run to)')
    ap.add_argument('--pc-dump', default='', help='comma-separated recorded positions that also dump per-PC VM')
    ap.add_argument('--check-preload', help='format string {p}: a TP-independent x_preload.hex to compare with')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if TP != 8 or GROUPS != 3072 or I.SU_WIDTH != 64 or G.KV_FMT != 'fp8':
        raise SystemExit('requires QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8')
    vec_check = self_check()
    print('vectorised reductions', vec_check, flush=True)
    tokens = [int(t) for t in a.tokens.read_text().split()]
    rec = sorted(int(p) for p in a.positions.split(','))
    dump = {int(p) for p in a.pc_dump.split(',') if p}
    last = rec[-1]
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    z = np.load(a.embedding_npz)
    emb = {}
    for t, sc, cd in zip(z['tokens'], z['scales'], z['codes']):
        x = (cd.view(np.int8).astype(np.float32) * np.float32(G.from_bits(np.uint32(sc) << np.uint32(16)))).astype(np.float32)
        emb[int(t)] = (x, int(sc), cd.copy())
    vm_map, _ = FP.vm_map()
    XB = vm_map['X']
    images = [[PO.StageImage(a.layer_dirs.format(layer=n, die=d), n) for d in range(8)] for n in range(a.layers)]
    lowered = [[lower_image(im.dir, layer=n) for im in ims] for n, ims in enumerate(images)]
    masks = []
    for n in range(a.layers):
        if any(im.descriptors != images[n][0].descriptors for im in images[n]):
            raise ValueError('TP8 descriptor mismatch')
        m = np.ones(FP.vm_map()[1], dtype=np.bool_)
        for lo, hi in lowered[n][0]['removed_intermediate_intervals'].values():
            m[lo:hi] = False
        masks.append(m)
    record = {'schema': 'opentallas.qwen-tp8-layer-gold.v1', 'status': 'ISA_golden_only', 'tp': 8, 'groups': GROUPS,
              'su_width': I.SU_WIDTH, 'kv_format': G.KV_FMT, 'layers': a.layers, 'positions': rec,
              'pc_dump_positions': sorted(dump), 'tokens_sha256': sha(a.tokens), 'embedding_npz_sha256': sha(a.embedding_npz),
              'collective_profile': 'production_tp8_two_level (rank 4*DIE+PKG, pair r[p]+r[p+4], ((P0+P1)+P2)+P3)',
              'programme': 'original 29-instruction checkpoint programme executed; effects keyed by the fused 25-instruction '
                           'candidate PC (lower_image original_to_candidate_pc; source PCs 11..14 = fused attention, '
                           'recorded at source PC 15 = candidate PC 11)',
              'layer_image_sha256': {f'L{n}': [im.image_sha for im in ims] for n, ims in enumerate(images)},
              'fused_program_sha256': {f'L{n}': [lw['candidate_program_sha256'] for lw in lws] for n, lws in enumerate(lowered)},
              'original_to_candidate_pc': lowered[0][0]['original_to_candidate_pc'],
              'source_sha256': {p: sha(GROOT / p) for p in (
                  'tools/hdc_golden.py', 'tools/hdc_program.py', 'tools/hdc_isa.py', 'tools/hdc_qwen_fullshape_isa_w12.py',
                  'tools/hdc_qwen_fullshape_program_w12.py', 'tools/qwen_rom_position_oracle_w12.py',
                  'tools/qwen_o4_layer0_oracle_w12.py', 'tools/qwen_tp8_native_layer_oracle.py',
                  'tools/qwen_tp8_payload_fused_lower.py')} | {'tools/qwen_layerbench/qwen_tp8_layer_gold.py': sha(__file__)},
              'vectorised_reductions_self_check': vec_check,
              'per_position': {},
              'claim_boundary': 'TP8 ISA golden over a real prompt (positions < P = golden prefill by sequential decode). '
                                'Not an RTL verdict.'}
    machines = [[GoldMachine(im, last + 1) for im in ims] for ims in images]
    t0 = time.time()
    for p in range(last + 1):
        tok = tokens[p]
        x = emb[tok][0]
        recording, dumping = p in rec, p in dump
        for d in range(8):
            machines[0][d].vm[:] = 0
            machines[0][d].vm[XB:XB + 4096] = x
        if recording:
            pdir = out / f'P{p}'
            (pdir / 'kv_pre').mkdir(parents=True, exist_ok=True)
            (pdir / 'kv_at_P').mkdir(parents=True, exist_ok=True)
            body = ''.join(f'{int(v):08x}\n' for v in G.bits(x))
            (pdir / 'x_preload.hex').write_text('@1000\n' + body)
            (pdir / 'embedding_row.json').write_text(json.dumps(
                {'token': tok, 'scale_bf16': f'{emb[tok][1]:04x}', 'codes_hex': emb[tok][2].tobytes().hex()}) + '\n')
            prec = {'token': tok, 'x_preload_sha256': sha(pdir / 'x_preload.hex'), 'layer_x_sha256': {},
                    'kv_pre_sha256': {}, 'kv_at_P_sha256': {}, 'effects': {}}
            if a.check_preload:
                ref = Path(a.check_preload.format(p=p))
                if ref.is_file():
                    prec['x_preload_equals_reference'] = ref.read_text() == (pdir / 'x_preload.hex').read_text()
                    if not prec['x_preload_equals_reference']:
                        raise SystemExit(f'x_preload differs from {ref}')
        for n in range(a.layers):
            ms, ims = machines[n], images[n]
            if n:
                for d in range(8):
                    ms[d].vm[:] = machines[n - 1][d].vm
            for d in range(8):
                ms[d].pos = p
            if recording:
                for d in range(8):
                    path = pdir / 'kv_pre' / f'L{n}_die{d}.npy'
                    np.save(path, G.bits(ms[d].kv).astype(np.uint32))
                    prec['kv_pre_sha256'][f'L{n}_die{d}'] = sha(path)
            with FP.program_geometry(vm_map):
                dyns = [P.dyn_values(m.lay, token=tok, pos=p) for m in ms]
                desc = ims[0].descriptors
                for si, seg in enumerate(desc):
                    first = seg['program_base']
                    end = desc[si + 1]['program_base'] if si + 1 < len(desc) else len(ims[0].program)
                    for d, (m, im, dyn) in enumerate(zip(ms, ims, dyns)):
                        ddir = pdir / f'die{d}' / f'L{n}' if dumping else None
                        if ddir is not None:
                            ddir.mkdir(parents=True, exist_ok=True)
                        for pc in range(first, end):
                            f = im.program[pc]
                            if f['unit'] == I.UNIT_ME:
                                m.me(f, dyn)
                            elif f['unit'] == I.UNIT_SU:
                                m.su(f, dyn)
                            if ddir is None:
                                continue
                            eff = prec['effects'].setdefault(f'L{n}_die{d}', {})
                            if pc not in range(11, 15) and f['unit']:
                                cpc = lowered[n][d]['original_to_candidate_pc'][11 if pc == 15 else pc]
                                path = ddir / f'candidate_pc{cpc}_vm.npz'
                                np.savez_compressed(path, vm_bits=G.bits(m.vm), defined_effect_mask=masks[n])
                                eff[str(cpc)] = {'source_pc': pc, 'full_VM_sha256': sha(path)}
                                if f['unit'] == I.UNIT_SU and f['dst'] == I.DST_KV:
                                    cnt = f['su_nin'] + dyn[f['su_d_nin']]
                                    adr = m.stream(f, dyn, 'd', f['su_nout'], cnt)
                                    kp = ddir / f'candidate_pc{cpc}_KV_commits.npz'
                                    np.savez_compressed(kp, element_addresses=adr, quantized_FP32_bits=G.bits(m.kv[adr]))
                                    eff[str(cpc)]['KV_commit_sha256'] = sha(kp)
                            if pc == 10:
                                eff['Q_input'] = bits_hex(ddir / 'Q_input_fp32.hex', m.vm[vm_map['QR']:vm_map['QR'] + 512])
                                eff['new_K_row'] = bits_hex(ddir / 'new_K_row_fp32.hex', m.kv[m.kidx[p]])
                                eff['new_V_row'] = bits_hex(ddir / 'new_V_row_fp32.hex', m.kv[m.vidx[p]])
                            if pc == 15:
                                eff['ATTN'] = bits_hex(ddir / 'ATTN_fp32.hex', m.vm[vm_map['ATTN']:vm_map['ATTN'] + 512])
                    if seg['kind'] == P.COLL_ALLREDUCE:
                        lo, hi = seg['vm_word'] * 16, (seg['vm_word'] + seg['words']) * 16
                        parts = [m.vm[lo:hi].copy() for m in ms]
                        folded = production_tp8_fold(parts)
                        for d, m in enumerate(ms):
                            m.vm[lo:hi] = folded
                            if dumping:
                                eff = prec['effects'].setdefault(f'L{n}_die{d}', {})
                                ddir = pdir / f'die{d}' / f'L{n}'
                                eff[f'collective{si}_partial'] = bits_hex(ddir / f'collective{si}_partial.hex', parts[d])
                                eff[f'collective{si}_return'] = bits_hex(ddir / f'collective{si}_return.hex', folded)
                    elif seg['kind'] != P.COLL_END:
                        raise ValueError('unexpected layer collective')
            if recording:
                for d in range(8):
                    m = ms[d]
                    kel, vel = [int(i) for i in m.kidx[p]], [int(i) for i in m.vidx[p]]
                    path = pdir / 'kv_at_P' / f'L{n}_die{d}.json'
                    path.write_text(json.dumps({'k_elem': kel, 'k_bits': [f'{int(b):08x}' for b in G.bits(m.kv[kel])],
                                                'v_elem': vel, 'v_bits': [f'{int(b):08x}' for b in G.bits(m.kv[vel])]}) + '\n')
                    prec['kv_at_P_sha256'][f'L{n}_die{d}'] = sha(path)
                    prec['layer_x_sha256'][f'L{n}_die{d}'] = bits_hex(pdir / f'L{n:02d}_die{d}_x.hex', m.vm[XB:XB + 4096])
        if recording:
            record['per_position'][str(p)] = prec
            (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        if p % 64 == 0 or recording:
            print(f'position {p} done ({time.time() - t0:.0f} s)', flush=True)
    record['wall_seconds'] = round(time.time() - t0, 1)
    (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'positions': rec, 'wall_seconds': record['wall_seconds']}))


if __name__ == '__main__':
    main()
