#!/usr/bin/env python3
"""TOK-FUNC3-QW (10-21) stage "chain": KV-die attention vectors from the REAL token (P8191, the stg fixtures' token).

For layer L (TP8 compute die 0 = TP4 die 0, query heads 0..3, KV head 0):
  q    = L<L>_qk.npz gold_q   (512 fp32 = 4 x 128: the QR rows the compute-die RTL produced bit-exact in stage stg/qk)
  K, V = kv_pre/L<L>_die0.npy (TP4 die-0 FP8 KV window, head 0) with position P's row = L<L>_qk.npz gold_k / gold_v
         (the K/V rows the compute-die RTL produced bit-exact in stage stg/qk), ctx = P + 1
and writes the release KV vehicle's vector dir (q.hex / kv.hex / gold.hex / check.hex / meta.json, the exact format of
tools/qwen_tp8_attention_native.py vectors) so the PRESERVED tb_kvattn_rel binary runs the token's real attention.

Golden = tools/qwen_tp8_attention_native.py arithmetic (TP8 native: 4 q heads / 1 KV head, S128 / PV256 at 3072 groups).
Hand-off evidence (no claim beyond it):
  tp4_repro   R.golden_die at the TP4 split (S128 / PV512, 6144 groups) on the same q/K/V must equal the TP4 ISA golden
              ATTN (= L<L>_mat_od.npz o_x, the od stage's input) bit-exact: proves q, the KV layout and the P row.
  tp8_vs_tp4  word diff between the TP8-native result (what the KV RTL computes) and the TP4 ATTN (what the od bench was
              fed): the TP8/TP4 PV-split rounding difference, a golden-family split (no 36-layer TP8 token golden exists).
usage: kv_real_vectors.py --fx DIR --kv-pre DIR --layer L --out DIR [--tools DIR]
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--fx', type=Path, required=True)
ap.add_argument('--kv-pre', type=Path, required=True)
ap.add_argument('--layer', type=int, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--tools', type=Path, default=Path(__file__).resolve().parents[1])
a = ap.parse_args()
sys.path.insert(0, str(a.tools))
os.environ.setdefault('HDC_SU_WIDTH', '8')
import qwen_tp8_attention_native as N  # noqa: E402
R = N.R
G = R.G

L = a.layer
qk = np.load(a.fx / f'L{L}_qk.npz')
od = np.load(a.fx / f'L{L}_mat_od.npz')
pos = int(qk['pos'])
ctx = pos + 1
kv = np.load(a.kv_pre / f'L{L}_die0.npy').astype(np.uint32)
if kv.shape != (4194304,):
    raise SystemExit(f'kv_pre shape {kv.shape}')
HD, T = 128, 8192
t = np.arange(T)[:, None]; d = np.arange(HD)[None, :]
k_idx = (t // 16) * 2048 + d * 16 + (t % 16)                  # head 0 K window (TP4 die layout, 16-position tiles)
v_idx = 2 * 1048576 + t * HD + d                             # head 0 V window
K = G.from_bits(kv[k_idx]).astype(np.float32)
V = G.from_bits(kv[v_idx]).astype(np.float32)
pre_row_zero = bool(not kv[k_idx[pos]].any() and not kv[v_idx[pos]].any())
K[pos] = qk['gold_k']; V[pos] = qk['gold_v']
K = K[:ctx, None, :]; V = V[:ctx, None, :]
q = qk['gold_q'].reshape(4, HD).astype(np.float32)
fp8_ok = bool(np.array_equal(G.bits(G.to_fp8(K)), G.bits(K)) and np.array_equal(G.bits(G.to_fp8(V)), G.bits(V)))

# TP4 reproduction (S128 / PV512) vs the TP4 ISA ATTN the od stage consumed
R.NH, R.KVH, R.GQ, R.GROUPS = 4, 1, 4, 6144
R.S_SC, R.S_PV = G.attn_splits(HD, 6144)
tp4 = R.golden_die(q, K, V).reshape(-1)
attn_tp4 = od['o_x'].astype(np.float32)
tp4_repro = int((G.bits(tp4) != G.bits(attn_tp4)).sum())

# TP8 native vectors (exact tools/qwen_tp8_attention_native.py vectors() format)
N.configure(3072)
gold = R.golden_die(q, K, V)
a.out.mkdir(parents=True, exist_ok=True)
maxima, denom = [], []
for h in range(4):
    sc = G.mul(G.matvec_il(K[:, 0, :], G.to_bf16(q[h]), R.S_SC), R.SCALE)
    m = sc.max()
    maxima.append(G.bits(m))
    denom.append(G.bits(G.lane_sum(G.exp(G.add(sc, G.neg(m))))))
(a.out / 'q.hex').write_text(''.join(f'{int(b):08x}\n' for b in G.bits(q).reshape(-1)))
with (a.out / 'kv.hex').open('w') as f:
    for arr in (R.fp8_encode(K), R.fp8_encode(V)):
        for i in range(ctx):
            f.write(bytes(arr[i, 0, ::-1]).hex() + '\n')
(a.out / 'gold.hex').write_text(''.join(f'{int(b):08x}\n' for b in G.bits(gold).reshape(-1)))
(a.out / 'check.hex').write_text(''.join(f'{int(b):08x}\n' for b in np.concatenate([np.asarray(maxima), np.asarray(denom)])))
gb, tb = G.bits(gold).reshape(-1).astype(np.int64), G.bits(attn_tp4).astype(np.int64)
diff = gb != tb
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.out.glob('*.hex')}
meta = dict(schema='qwen-tp8-attention-native-v1', ctx=ctx, position=pos, seed=0, kind=f'real_token_L{L}',
            q_heads=4, kv_heads=1, hd=128, groups=3072, attn_splits=[R.S_SC, R.S_PV], q_transport='FP32',
            consumer_q='BF16 RNE', kv='FP8 E4M3', outputs=512, output_beats=32, input_beats=32, hashes=hashes,
            source_hashes=N.source_receipt(), qualification='REAL_TOKEN_ATTENTION_LAYER',
            real_token=dict(layer=L, position=pos, fx=str(a.fx), kv_pre=str(a.kv_pre / f'L{L}_die0.npy'),
                            q_from='L%d_qk.npz gold_q (stg qk RTL output, bit-exact)' % L,
                            p_row_from='L%d_qk.npz gold_k/gold_v (stg qk RTL output, bit-exact)' % L,
                            kv_pre_p_row_zero=pre_row_zero, kv_fp8_representable=fp8_ok,
                            tp4_repro_word_mismatch=tp4_repro,
                            tp8_vs_tp4_attn=dict(words_differ=int(diff.sum()),
                                                 max_ulp=int(np.abs(gb - tb)[diff].max()) if diff.any() else 0)))
(a.out / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n')
print('KVREAL', L, json.dumps(meta['real_token']))
sys.exit(0 if tp4_repro == 0 and pre_row_zero else 3)
