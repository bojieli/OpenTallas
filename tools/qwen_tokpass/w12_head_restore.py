#!/usr/bin/env python3
"""TOKEN-PASS-QWEN 2026-10-18: restore a swept W12 HEAD stage image (matrix_int8 / matrix_scale_bf16 / crom) from the
pinned prep npz, the head twin of tools/exactness/w12_layer_restore.py (which selects kind == 'layer' only).

    w12_head_restore.py PREP DIE IMGDIR      (source root; QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8)

Writes the matrices with the emitter's engine_word_arrays / word_hex (compact first, then the padded form), accepts ONLY
when all three sha256 equal the prep's recorded image pins, then tools/exactness/w12_head_stage.py adds the program."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, 'tools')
from hdc_qwen_layer0_rom_w12 import engine_word_arrays, word_hex
from hdc_qwen_fullshape_placement_w12 import GROUPS
import hdc_isa as I
W, IL = I.W_LANES, I.INTERLEAVE
prep, die, out = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
P = json.loads((prep / 'prep.json').read_text())
rec = next(r for r in P['images'] if r['kind'] == 'head' and r['die'] == die)
rows = rec['layout']
z = np.load(prep / rec['npz'])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
u16 = lambda f: (np.asarray(f, dtype=np.float32).view(np.uint32) >> 16).astype(np.uint16)
out.mkdir(parents=True, exist_ok=True)
cb = z['crom'].astype(np.float32).view(np.uint32)
(out / 'crom.hex').write_text(''.join(f'{(int(hi) << 32) | int(lo):016x}\n' for lo, hi in cb))
res = {}
for compact in (True, False):
    with open(out / 'matrix_int8.hex', 'w') as cf, open(out / 'matrix_scale_bf16.hex', 'w') as sf:
        for r in rows:
            codes, scales = z[f"codes_{r['name']}"], u16(z[f"scales_{r['name']}"])
            for a, (code, scale) in enumerate(engine_word_arrays(codes, scales, split=r['split'], raw_partial=False)):
                if not compact or a < r['code_span_words']:
                    cf.write(word_hex(code, 8) + '\n')
                if not compact or a < r['scale_span_words']:
                    sf.write(word_hex(scale, 16) + '\n')
    res = {nm: sha(out / nm) == rec['image_sha256'][nm] for nm in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex')}
    if all(res.values()):
        break
print(json.dumps({'head_die': die, 'compact': compact, 'ok': res}))
sys.exit(0 if all(res.values()) else 1)
