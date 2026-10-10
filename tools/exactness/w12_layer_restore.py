#!/usr/bin/env python3
"""Restore a swept W12 LAYER stage image from the pinned prep npz (token-exact 2026-10-09).

    w12_layer_restore.py PREP LAYER DIE IMGDIR [--compact]     (source root; QWEN_O4_TP / QWEN_O4_GROUPS /
                                                                 HDC_SU_WIDTH=1024 / HDC_KV_FMT set)

tools/hdc_qwen_layer0_rom_w12.emit replayed with the matrices taken from the prep npz instead of the checkpoint: the
decoded codes / BF16 scales (o / down scales from the constant ROM at the post-TP scale bases), the prep's matrix
layout, engine_word_arrays + word_hex for matrix_int8 / matrix_scale_bf16 (padding words as the emitter writes them),
crom.hex from the decoded constant ROM, program / segments verbatim from the prep's recorded layout-image words.
Accepted ONLY if matrix_int8 / matrix_scale_bf16 / crom sha256 equal the prep pins and program / segments equal the
prep's recorded layout-image programs; writes layer<n>_rom.json (matrix_layout, post_tp_scale_bases, die, layer)."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, 'tools')
import hdc_qwen_fullshape_program_w12 as FP
from hdc_qwen_layer0_rom_w12 import engine_word_arrays, word_hex
from hdc_qwen_fullshape_placement_w12 import GROUPS
import hdc_isa as I
W, IL = I.W_LANES, I.INTERLEAVE
prep, layer, die, out = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
compact = '--compact' in sys.argv
P = json.loads((prep / 'prep.json').read_text())
rec = next(r for r in P['images'] if r['kind'] == 'layer' and r['layer'] == layer and r['die'] == die)
rows = rec['layout']
z = np.load(prep / rec['npz'])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out.mkdir(parents=True, exist_ok=True)
u16 = lambda f: (np.asarray(f, dtype=np.float32).view(np.uint32) >> 16).astype(np.uint16)
crom = z['crom'].astype(np.float32)
n_o = next(r['rows'] for r in rows if r['name'] == 'o'); n_d = next(r['rows'] for r in rows if r['name'] == 'down')
bases = (len(crom) - n_o - n_d, len(crom) - n_d)
scale_depth = (rows[-1]['scale_end'] if compact else
               max(r['base'] + (r['rounds'] - 1) * (GROUPS // r['split']) * IL + (GROUPS - 1) * IL + IL for r in rows))
with open(out / 'matrix_int8.hex', 'w') as cf, open(out / 'matrix_scale_bf16.hex', 'w') as sf:
    for r in rows:
        codes, scales = z[f"codes_{r['name']}"], u16(z[f"scales_{r['name']}"])
        for a, (code, scale) in enumerate(engine_word_arrays(codes, scales, split=r['split'],
                                                              raw_partial=r['name'] in ('o', 'down'))):
            if not compact or a < r['code_span_words']:
                cf.write(word_hex(code, 8) + '\n')
            if not compact or a < r['scale_span_words']:
                sf.write(word_hex(scale, 16) + '\n')
    for _ in range(rows[-1]['scale_end'] if compact else rows[-1]['end'], scale_depth):
        sf.write('3f80' * W + '\n')
cb = crom.view(np.uint32)
(out / 'crom.hex').write_text(''.join(f'{(int(hi) << 32) | int(lo):016x}\n' for lo, hi in cb))
# program / segments: the layout image's own words as the prep recorded them (identical for every layer of a die). Today's
# FP.profile re-emits the same words except three SU chase thresholds (timing only, the R-ARITH order is width-free), so
# the recorded words are restored verbatim and sha-checked against the recorded pin.
pg = P['programs'][f'layer_d{die}']
(out / 'program.hex').write_text('\n'.join(pg['program']) + '\n')
(out / 'segments.hex').write_text('\n'.join(pg['segments']) + '\n')
(out / f'layer{layer}_rom.json').write_text(json.dumps({'layer': layer, 'die': die, 'matrix_layout': rows,
    'post_tp_scale_bases': list(bases), 'restored_by': 'tools/exactness/w12_layer_restore.py (prep npz, sha-checked)'},
    indent=1) + '\n')
ok = {nm: sha(out / nm) == rec['image_sha256'][nm] for nm in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex')}
ok['program'] = sha(out / 'program.hex') == pg['program_sha256']
ok['segments'] = sha(out / 'segments.hex') == pg['segments_sha256']
print(json.dumps({'layer': layer, 'die': die, 'compact': compact, 'ok': ok}))
sys.exit(0 if all(ok.values()) else 1)
