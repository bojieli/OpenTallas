#!/usr/bin/env python3
"""QW-KVATTN (TOK.QW.KV, 10-18): the KV-die attention operands of one decode position, from the TP4 ISA golden.

Input: kv_attn_gold.py output (L<n>_vm.npy, L<n>_kv.npy, L<n>_me_kv.json, P<pos>/ = the oracle's own outputs).
For layer n, TP4 die d, KV head g (q heads 4g..4g+3 of the die):
  q      = VM QR region (the roped q the score op reads, FP32; the attention service rounds it to BF16)
  K, V   = the die's K/V store AFTER the layer (= history + the row written at P), rows 0..P, FP8-valued FP32
  isa    = the ISA golden's attention output (VM ATTN region, the o-projection's input), FP32
Checks (record.json):
  * fixture identity: P<pos>/L<nn>_die<d>_x.hex and kv_at_P/L<n>_die<d>.json equal the real-prefill fixtures (--fx)
  * the KV die reference tools/qwen_nearhbm_attn_ref.golden_die (the reference the KV die attention RTL is qualified
    against, R) at the ISA's own splits (score split / P.V split from the me_kv ISA fields) == isa, bit for bit
  * the same reference at the KV die's TP8 P.V split 256 (tools/qwen_tp8_attention_native.configure(3072), the split
    qkd_pvw_die_t / qkd_pv_fin_s implement) vs isa: number of differing words (a TP8 die cannot reproduce TP4 P.V order)
Vectors (--vec DIR/L<n>_d<d>_g<g>/, the tb_qwen_tp8_attention_native_service_w16 format): q.hex (512 FP32), kv.hex (K rows
then V rows, 128 FP8 bytes each, dim 0 at the LSB byte), gold.hex (the TP8 reference, 512 FP32), isa.hex (the TP4 ISA output).
Mutant witnesses: --mutant shift (history row P-1 replaced by row P-2) / pos (context length P instead of P+1, i.e. the
row written at P is not attended): kv.hex / ctx carry the mutated operands, gold.hex the TRUE reference, so the bench run
on them must FAIL (mutant_changes_ref_words = how many reference words the mutation moves).
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gold', type=Path, required=True)
    ap.add_argument('--fx', type=Path, required=True, help='realmem/P<pos> of the real-prefill fixtures')
    ap.add_argument('--ksrc', type=Path, required=True, help='KV die source tree (tools/qwen_nearhbm_attn_ref.py)')
    ap.add_argument('--layers', default='0,1')
    ap.add_argument('--vec', type=Path)
    ap.add_argument('--mutant', choices=('none', 'shift', 'pos'), default='none')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    os.environ.setdefault('HDC_SU_WIDTH', '8')
    sys.path.insert(0, str(a.ksrc / 'tools'))
    import hdc_golden as G
    import qwen_nearhbm_attn_ref as R
    TMAX, HD, NHD, KVD, W = 8192, 128, 8, 2, 16
    rec = {'schema': 'opentallas.qwen_layerbench.kv_attn_vectors.v1', 'gold': str(a.gold), 'fx': str(a.fx),
           'ksrc': str(a.ksrc), 'mutant': a.mutant, 'layers': {},
           'ref_sha256': {p: sha(a.ksrc / p) for p in ('tools/qwen_nearhbm_attn_ref.py', 'tools/hdc_golden.py')}}
    ok = True
    for n in [int(x) for x in a.layers.split(',')]:
        meta = json.loads((a.gold / f'L{n}_me_kv.json').read_text())
        pos, vmap = meta['pos'], meta['vm_map']
        sc_f, pv_f = meta['calls'][0]['fields'], meta['calls'][1]['fields']
        s_sc, s_pv = 1 << sc_f['me_split'], 1 << pv_f['me_split']
        vm = np.load(a.gold / f'L{n}_vm.npy')
        kv = np.load(a.gold / f'L{n}_kv.npy')
        pdir = a.gold / f'P{pos}'
        L = {'pos': pos, 'isa_splits': {'score': s_sc, 'pv': s_pv}, 'fixture_identity': {}, 'heads': {}}
        for d in range(4):
            fx_ok = (pdir / f'L{n:02d}_die{d}_x.hex').read_bytes() == (a.fx / f'L{n:02d}_die{d}_x.hex').read_bytes() and \
                    (pdir / 'kv_at_P' / f'L{n}_die{d}.json').read_bytes() == (a.fx / 'kv_at_P' / f'L{n}_die{d}.json').read_bytes()
            L['fixture_identity'][f'die{d}'] = bool(fx_ok)
            ok &= fx_ok
            qall = vm[d, vmap['QR']:vmap['QR'] + NHD * HD].view(np.float32).reshape(NHD, HD)
            isa = vm[d, vmap['ATTN']:vmap['ATTN'] + NHD * HD].view(np.float32).reshape(NHD, HD)
            att = vm[d, vmap['ATT']:vmap['ATT'] + NHD * HD].view(np.float32).reshape(NHD, HD)
            st = kv[d].view(np.float32)
            T = pos + 1
            t = np.arange(T)
            kv_v0 = KVD * TMAX * HD
            for g in range(KVD):
                # LayerZero.k_elem / v_elem (tools/hdc_qwen_fullshape_program_w12.py)
                kidx = ((g * (TMAX // W) + t[:, None] // W) * HD + np.arange(HD)[None, :]) * W + t[:, None] % W
                vidx = kv_v0 + (g * TMAX + t[:, None]) * HD + np.arange(HD)[None, :]
                K, V = st[kidx].copy(), st[vidx].copy()
                q = qall[4 * g:4 * g + 4].copy()
                Tm, Km, Vm = T, K.copy(), V.copy()
                if a.mutant == 'shift':
                    Km[pos - 1], Vm[pos - 1] = K[pos - 2], V[pos - 2]
                elif a.mutant == 'pos':
                    Tm = T - 1
                Kc, Vc = Km[:Tm, None, :], Vm[:Tm, None, :]
                R.NH, R.KVH, R.GQ = 4, 1, 4
                R.S_SC, R.S_PV = s_sc, s_pv
                ref_isa = R.golden_die(q, Kc, Vc)
                R.S_SC, R.S_PV = G.attn_splits(HD, 3072)          # the KV die's TP8 splits (qwen_tp8_attention_native)
                ref_tp8 = R.golden_die(q, Kc, Vc)
                # a mutant's bench gold stays the TRUE reference (unmutated operands): the mutated K/V must FAIL it
                gold_tp8 = ref_tp8 if a.mutant == 'none' else R.golden_die(q, K[:, None, :], V[:, None, :])
                tgt = isa[4 * g:4 * g + 4]
                h = {'isa_ref_eq_isa': int(np.sum(G.bits(ref_isa) != G.bits(tgt))),
                     'tp8_splits': [int(R.S_SC), int(R.S_PV)],
                     'tp8_ref_diff_words_vs_isa': int(np.sum(G.bits(ref_tp8) != G.bits(tgt))),
                     'tp8_ref_max_abs_rel': float(np.max(np.abs(ref_tp8 - tgt) / np.maximum(np.abs(tgt), 1e-30))),
                     'att_region_equals_attn': bool(np.array_equal(G.bits(att[4 * g:4 * g + 4]), G.bits(tgt)))}
                L['heads'][f'd{d}_g{g}'] = h
                if a.mutant == 'none':
                    ok &= h['isa_ref_eq_isa'] == 0
                else:
                    h['mutant_changes_ref_words'] = int(np.sum(G.bits(ref_tp8) != G.bits(gold_tp8)))
                if a.vec:
                    o = a.vec / f'L{n}_d{d}_g{g}'
                    o.mkdir(parents=True, exist_ok=True)
                    (o / 'q.hex').write_text(''.join(f'{int(b):08x}\n' for b in G.bits(q).reshape(-1)))
                    with (o / 'kv.hex').open('w') as f:
                        for arr in (R.fp8_encode(Kc), R.fp8_encode(Vc)):
                            for r in range(Tm):
                                f.write(bytes(arr[r, 0, ::-1]).hex() + '\n')
                    (o / 'gold.hex').write_text(''.join(f'{int(b):08x}\n' for b in G.bits(gold_tp8).reshape(-1)))
                    (o / 'isa.hex').write_text(''.join(f'{int(b):08x}\n' for b in G.bits(tgt).reshape(-1)))
                    (o / 'ctx').write_text(f'{Tm}\n')
                print(f'L{n} d{d} g{g}: ref@isa-splits diff {h["isa_ref_eq_isa"]}  ref@tp8 diff {h["tp8_ref_diff_words_vs_isa"]}/512 '
                      f'(max rel {h["tp8_ref_max_abs_rel"]:.2e})', flush=True)
        rec['layers'][str(n)] = L
    rec['verdict'] = 'PASS' if ok else 'FAIL'
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print('KVATTN_VECTORS', rec['verdict'])
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
