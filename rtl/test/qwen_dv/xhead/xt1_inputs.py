#!/usr/bin/env python3
"""QC-TOK 10-24: regenerate the XT1 bench inputs (gold_near.json, gold_far.json, masks/) after the TOKe-QWM record
inputs were lost with ot-gold2.  Used by tools/die_plan/bind_smoke.py --inputs DIR.

    QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8 PYTHONPATH=tools \\
    xt1_inputs.py --snapshot SNAP --img IMG --out OUT [--token 785]

1. IMG = TP8 rank-0 L0 die-0 code-ROM image, made by tools/hdc_qwen_layer0_rom_w12.py --die 0 --layer 0 --compact-banks
   from the pinned checkpoint Qwen/Qwen3-8B@b968826d (lock 5cd62731...).  matrix_int8.hex MUST equal the committed pin
   results/arch/qwen_tp8_native_dispatch_1014/actual_checkpoint_layer0/die0/layer0_rom.json (8f48f3f4...): the REAL
   weights the record used (the record masks are this image's bytes; xt1_prep checks the identity + the image sha).
2. fx: w = the image's own qkv / o / gu / down int8 matrices decoded by the oracle's StageImage (independent of the
   xt1_prep layout mapping, which then re-checks every cluster byte: 'layout mismatches 0' required);
   x = STAND-IN, NOT the record's P8191 realmem activations (those need the GPU TP8 golden run): the RMS-normalised
   checkpoint embedding row of --token (qkv / gu, norm gains are folded into W), its first 512 elements (o) and first
   1536 elements (down).  The golden is recomputed from (w, x) by xt1_prep (hdc_golden level-6 parts), so the bench
   stays bit-exact; only the data values differ from the record.
3. xt1_prep.py prep_c2 (near, cid 2) / prep_c3 (far, cid 3) -> OUT/gold_near.json, OUT/gold_far.json, OUT/masks (both
   clusters' masks = the record's masks_fixed), OUT/MANIFEST.json (sha256 of every input + provenance).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PIN = REPO / 'results/arch/qwen_tp8_native_dispatch_1014/actual_checkpoint_layer0/die0/layer0_rom.json'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--img', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--token', type=int, default=785)
    a = ap.parse_args()
    if os.environ.get('QWEN_O4_TP') != '8' or os.environ.get('QWEN_O4_GROUPS') != '3072':
        raise SystemExit('set QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64')
    pin = json.loads(PIN.read_text())['image_sha256']['matrix_int8.hex']
    got = sha(a.img / 'matrix_int8.hex')
    if got != pin:
        raise SystemExit(f'matrix_int8.hex {got} != committed pin {pin}')
    sys.path.insert(0, str(REPO / 'tools'))
    import qwen_rom_position_oracle_w12 as PO
    im = PO.StageImage(a.img, 0)
    mats = {m['name']: im.matrix(m)[0].astype(np.int8) for m in im.manifest['matrix_layout']}

    from safetensors import safe_open
    idx = json.loads((a.snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    key = 'model.embed_tokens.weight'
    with safe_open(str(a.snapshot / idx[key]), framework='pt', device='cpu') as sf:
        e = sf.get_slice(key)[a.token:a.token + 1].float().numpy()[0].astype(np.float32)
    x = (e / np.sqrt(np.mean(e.astype(np.float64) ** 2) + 1e-6)).astype(np.float32)

    fx = a.out / 'fx'
    fx.mkdir(parents=True, exist_ok=True)
    np.savez(fx / 'L0_mat_qkv.npz', w=mats['qkv'], x=x)
    np.savez(fx / 'L0_mat_gu.npz', w=mats['gu'], x=x)
    np.savez(fx / 'L0_mat_od.npz', o_w=mats['o'], o_x=x[:512], down_w=mats['down'], down_x=x[:1536])
    prep = []
    for tag, cid in (('c2', 2), ('c3', 3)):
        d = a.out / f'prep_{tag}'
        r = subprocess.run([sys.executable, str(HERE / 'xt1_prep.py'), '--img', str(a.img), '--fx', str(fx), '--cid',
                            str(cid), '--out', str(d)], capture_output=True, text=True)
        (a.out / f'prep_{tag}.log').write_text(r.stdout + r.stderr)
        if r.returncode or 'PREP DONE' not in r.stdout:
            raise SystemExit(f'xt1_prep {tag} failed:\n{r.stdout[-2000:]}{r.stderr[-2000:]}')
        bad = [ln for ln in r.stdout.splitlines() if 'layout mismatches' in ln and 'layout mismatches 0 ' not in ln]
        if bad:
            raise SystemExit(f'layout mismatch {tag}: {bad}')
        prep.append(r.stdout.strip())
    shutil.copyfile(a.out / 'prep_c2/gold.json', a.out / 'gold_near.json')
    shutil.copyfile(a.out / 'prep_c3/gold.json', a.out / 'gold_far.json')
    (a.out / 'masks').mkdir(exist_ok=True)
    for tag in ('c2', 'c3'):
        for f in (a.out / f'prep_{tag}/masks').iterdir():
            shutil.copyfile(f, a.out / 'masks' / f.name)
    man = dict(schema='opentallas.xt1_inputs.v1', tool='rtl/test/qwen_dv/xhead/xt1_inputs.py',
               checkpoint=dict(repo='Qwen/Qwen3-8B', revision=a.snapshot.name,
                               lock='compiler/models/qwen3-8b/checkpoint_source.json'),
               image=dict(dir=str(a.img), files={f.name: sha(f) for f in sorted(a.img.iterdir())},
                          matrix_int8_pin=pin, pin_file=str(PIN.relative_to(REPO)), pin_match=True),
               weights='REAL: TP8 die-0 L0 code-ROM bytes of the pinned checkpoint (= record masks)',
               x=f'STAND-IN (not the record P8191 activations): RMS-normalised embedding row of token {a.token}; '
                 'qkv/gu x[0:4096], o x[0:512], down x[0:1536]',
               golden='xt1_prep.py level-6 parts recomputed on (w, x)', prep=prep,
               files={str(p.relative_to(a.out)): sha(p) for p in sorted(a.out.rglob('*')) if p.is_file()
                      and not p.name.startswith('MANIFEST')})
    (a.out / 'MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')
    print('XT1_INPUTS DONE', a.out)


if __name__ == '__main__':
    main()
