#!/usr/bin/env python3
"""Usage (source root, QWEN_O4_TP / QWEN_O4_GROUPS set): w12_head_restore.py PREP DIE OUTDIR.
token-exact 2026-10-09 (padding scales are BF16 1.0 as the emitter writes them): restore a swept W12 head stage image (matrix_int8 / matrix_scale_bf16 / crom hex) from the
pinned prep npz by inverting qwen_o4_layer0_oracle_w12.Image.matrix + read_crom; accepted ONLY if every file's sha256
equals the pin recorded when the npz was decoded (prep.json image_sha256)."""
import hashlib, json, sys, numpy as np
from pathlib import Path
sys.path.insert(0, 'tools')
import hdc_isa as I
import hdc_golden as G
from hdc_qwen_fullshape_placement_w12 import GROUPS
W, IL = I.W_LANES, I.INTERLEAVE
prep, die, out = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
rec = next(r for r in json.loads((prep / 'prep.json').read_text())['images'] if r['kind'] == 'head' and r['die'] == die)
meta = rec['layout'][0]
z = np.load(prep / rec['npz'])
out.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
groups, n, k, split = GROUPS, meta['rows'], meta['columns'], meta['split']
per_round, kc, rounds = groups // split, meta['k_per_split'], meta['rounds']
count, lanes = meta['code_span_words'], groups * W
full = np.zeros((rounds * per_round * IL * W, k), dtype=np.int8)
full[:n] = z['codes_lm_head']
buf = full.reshape(rounds, per_round, IL, W, split, kc).transpose(0, 5, 2, 1, 4, 3).reshape(-1, lanes)
assert buf.shape[0] >= count
with open(out / 'matrix_int8.hex', 'w') as f:
    for a in range(count):
        f.write(buf[a][::-1].tobytes().hex() + '\n')
sc = z['scales_lm_head'].astype(np.float32).view(np.uint32)
assert np.all((sc & 0xFFFF) == 0)
s16 = np.full(meta['scale_span_words'] * W, 0x3F80, dtype='>u2'); s16[:n] = (sc >> 16).astype(np.uint16)
with open(out / 'matrix_scale_bf16.hex', 'w') as f:
    for a in range(meta['scale_span_words']):
        f.write(s16[a * W:(a + 1) * W][::-1].tobytes().hex() + '\n')
cr = z['crom'].astype(np.float32).view(np.uint32)
with open(out / 'crom.hex', 'w') as f:
    for lo, hi in cr:
        f.write(f'{int(hi):08x}{int(lo):08x}\n')
got = {nm: sha(out / nm) for nm in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex')}
ok = {nm: got[nm] == rec['image_sha256'][nm] for nm in got}
print(json.dumps({'die': die, 'ok': ok}))
sys.exit(0 if all(ok.values()) else 1)
