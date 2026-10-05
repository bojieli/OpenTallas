#!/usr/bin/env python3
"""AR golden of a token block through all 36 layers and the lm_head: per-position argmax.

The ISA golden of tools/qwen_o4_token_oracle_w12.py (pinned TP4 layer and head
programs, hdc_golden arithmetic, rank-order fold), run autoregressively over the
block tokens t0 .. t(p-1) at positions 0 .. p-1: layer by layer, each layer's
KV window carried from position to position.  Writes every position's X after
layer 35 as one sparse preload at the verify map's X bases (the input of the
p-position head stage of tools/qwen_rom_verify_program_w12.py) and the
per-position argmax {token, logit bits} -- what the verify step's per-position
argmax must equal.  Not an RTL verdict.

  HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 \\
  qwen_rom_verify_head_oracle_w12.py --img-dirs '/home/ubuntu/w12/img_tp4/L{layer}-d{die}' \\
      --head-dirs '/home/ubuntu/w12/img_tp4/head-d{die}' --binding /home/ubuntu/w12/img_tp4/binding \\
      --tokens 0,50994,279,13 --preload-dir PDIR --x-bases 16384,109424,202464,295504 --out OUT
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_program_w12 as FP
import qwen_o4_layer0_oracle_w12 as L0
import qwen_o4_token_oracle_w12 as TO
import qwen_rom_verify_oracle_w12 as VO

ROOT = Path(__file__).resolve().parents[1]
TP, VM1 = L0.TP, L0.VM


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--img-dirs', required=True)
    ap.add_argument('--head-dirs', required=True)
    ap.add_argument('--binding', type=Path, required=True)
    ap.add_argument('--tokens', required=True)
    ap.add_argument('--preload-dir', type=Path, required=True)
    ap.add_argument('--x-bases', required=True)
    ap.add_argument('--layers', type=int, default=36)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--resume-head', action='store_true', help='skip the layers: x_after_layers.npy in --out')
    a = ap.parse_args()
    if I.SU_WIDTH != 1024 or G.SU_WIDTH != 1024 or G.KV_FMT != 'fp8':
        raise SystemExit('oracle requires HDC_SU_WIDTH=1024 and HDC_KV_FMT=fp8')
    tokens = [int(t) for t in a.tokens.split(',')]
    x_bases = [int(x) for x in a.x_bases.split(',')]
    p = len(tokens)
    if len(x_bases) != p:
        raise SystemExit('one X base per token')
    a.out.mkdir(parents=True, exist_ok=True)
    xs = [L0._preload_x(a.preload_dir / f'tok{t}' / 'vm_x_fp32.hex') for t in tokens]
    resume = a.out / 'x_after_layers.npy'
    if a.resume_head and resume.exists():
        xs = list(np.load(resume))
        a.layers_run = 0
    else:
        a.layers_run = a.layers
    rec = {'schema': 'opentallas.qwen-rom-verify-head-oracle.v1', 'status': 'ISA_golden_only', 'tokens': tokens,
           'positions': list(range(p)), 'layers': a.layers, 'x_bases': x_bases,
           'source_sha256': {q: VO.sha(ROOT / q) for q in (
               'tools/qwen_rom_verify_head_oracle_w12.py', 'tools/qwen_rom_verify_oracle_w12.py',
               'tools/qwen_o4_token_oracle_w12.py', 'tools/qwen_o4_layer0_oracle_w12.py', 'tools/hdc_golden.py',
               'tools/hdc_program.py', 'tools/hdc_isa.py')},
           'layer_x_sha256': {}}
    with FP.program_geometry(VM1):
        for n in range(a.layers_run):
            images = [VO.LayerImage(a.img_dirs.format(layer=n, die=d), n) for d in range(TP)]
            ms = [L0.DieMachine(im) for im in images]
            for j in range(p):
                for m in ms:
                    m.vm[VM1['X']:VM1['X'] + 4096] = xs[j]
                VO.run_program(ms, images, lambda im, pc, j=j: j)
                out = [m.vm[VM1['X']:VM1['X'] + 4096].copy() for m in ms]
                if any(not np.array_equal(G.bits(out[0]), G.bits(o)) for o in out[1:]):
                    raise SystemExit(f'dies disagree at layer {n} position {j}')
                xs[j] = out[0]
            rec['layer_x_sha256'][f'L{n}'] = [VO.sha_bytes(G.bits(x).tobytes()) for x in xs]
            VO._matrix_cached.cache_clear()
            print(f'layer {n} done', flush=True)
        np.save(a.out / 'x_after_layers.npy', np.stack(xs))   # checkpoint: the head can be re-run from here
        layout0 = json.loads(Path(a.img_dirs.format(layer=0, die=0), 'layer0_rom.json').read_text())['matrix_layout']
        heads = []
        for j in range(p):
            logits_all, per_die = [], []
            for d in range(TP):
                im = TO.HeadImage(a.head_dirs.format(die=d), a.binding, d)
                vm = np.zeros(L0.VM_ELEMS, dtype=np.float32)
                vm[VM1['X']:VM1['X'] + 4096] = xs[j]
                m = TO.HeadMachine(im, d, vm, layout0)
                dyn = P.dyn_values(m.lay, token=0, pos=j)
                for f in im.program:
                    if f['unit'] == I.UNIT_ME:
                        m.me(f, dyn)
                    elif f['unit'] == I.UNIT_SU:
                        m.su(f, dyn)
                logits_all.append(np.asarray(m.logits, dtype=np.float32))
                per_die.append({'argmax_local': m.argmax,
                                'logit_bits': f'{int(G.bits(np.float32(m.logits[m.argmax]))):08x}'})
            logits = np.concatenate(logits_all)
            tok = int(np.argmax(logits))
            top2 = np.sort(logits)[-2:]
            heads.append({'position': j, 'input_token': tokens[j], 'argmax_token': tok,
                          'logit_bits': f'{int(G.bits(np.float32(logits[tok]))):08x}',
                          'top2_margin': float(top2[1] - top2[0]), 'per_die': per_die})
            print(f'head position {j}: token {tok}', flush=True)
    with (a.out / 'vm_x_block.hex').open('w') as s:
        for j, base in enumerate(x_bases):
            s.write(f'@{base:x}\n')
            for b in G.bits(xs[j]):
                s.write(f'{int(b):08x}\n')
    rec['heads'] = heads
    rec['argmax_tokens'] = [h['argmax_token'] for h in heads]
    rec['emitter_source_drift'] = VO.LayerImage.drift
    rec['preload_block_sha256'] = VO.sha(a.out / 'vm_x_block.hex')
    (a.out / 'oracle.json').write_text(json.dumps(rec, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'argmax_tokens': rec['argmax_tokens']}))


if __name__ == '__main__':
    main()
