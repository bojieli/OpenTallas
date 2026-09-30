#!/usr/bin/env python3
"""ISA arithmetic oracle for one full Qwen3-8B O4 INT8 TP-2 token (token 0, position 0).

Extends tools/qwen_o4_layer0_oracle.py (unchanged arithmetic: dense matrices
by the golden contiguous K-split reduction, stream/attention instructions by
the ISA golden, TP-2 all-reduce by the golden fold in descriptor order) over
all 36 decoder layers and the lm_head stage:

  X(token 0) preload -> layer 0 .. layer 35 (per-layer images, program shared,
  a fresh zero KV window per layer, VM carried) -> final RMSNorm + TP-2 lm_head
  chunks with running argmax -> cross-die argmax (die row offset 75,968).

Writes die X after every layer, the head's normalized input, the per-die
running argmax/logit and the token.  Not an RTL verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa as QI
import hdc_qwen_fullshape_program as FP
import qwen_o4_layer0_oracle as L0

ROOT = Path(__file__).resolve().parents[1]
W, IL, GROUPS, TP = L0.W, L0.IL, L0.GROUPS, L0.TP
VM = L0.VM
HEAD_ROWS = 151936 // TP


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class LayerImage(L0.Image):
    """layer0_oracle.Image without the layer-0-only assertion."""

    def __init__(self, directory, layer):
        self.dir = Path(directory)
        self.manifest = json.loads((self.dir / f'layer{layer}_rom.json').read_text())
        if self.manifest['layer'] != layer or self.manifest['tp'] != TP:
            raise ValueError(f'expected layer {layer} TP2 images in {directory}')
        for name, digest in self.manifest['image_sha256'].items():
            if sha(self.dir / name) != digest:
                raise ValueError(f'image digest mismatch: {directory}/{name}')
        for name, digest in self.manifest['source_sha256'].items():
            if sha(ROOT / name) != digest:
                raise ValueError(f'emitter source drift: {name}')
        self.layout = {row['base']: row for row in self.manifest['matrix_layout']}
        self.program = [QI.decode_instruction(int(line, 16)) for line in (self.dir / 'program.hex').read_text().splitlines()]
        self.descriptors = [QI.decode_descriptor(int(line, 16)) for line in (self.dir / 'segments.hex').read_text().splitlines()]
        self.crom = read_crom(self.dir / 'crom.hex')


def read_crom(path):
    lo, hi = [], []
    with Path(path).open() as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith('@'):
                continue
            line = line.rjust(16, '0')
            hi.append(int(line[:8], 16))
            lo.append(int(line[8:16], 16))
    return np.stack((G.from_bits(np.array(lo, dtype=np.uint32)), G.from_bits(np.array(hi, dtype=np.uint32))), axis=1)


def run_layer(images, vms):
    machines = [L0.DieMachine(im) for im in images]
    for mach, vm in zip(machines, vms):
        mach.vm[:] = vm
    with FP.program_geometry(VM):
        dyns = [P.dyn_values(m.lay, token=0, pos=0) for m in machines]
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


class HeadImage:
    def __init__(self, directory, binding, die):
        self.dir = Path(directory)
        self.manifest = json.loads((self.dir / 'head_rom.json').read_text())
        if self.manifest['die'] != die:
            raise ValueError('head image die mismatch')
        for name, digest in self.manifest['image_sha256'].items():
            if sha(self.dir / name) != digest:
                raise ValueError(f'head image digest mismatch: {name}')
        geo = self.manifest['geometry']
        meta = {'name': 'lm_head', 'rows': HEAD_ROWS, 'columns': 4096, 'split': geo['split'],
                'k_per_split': geo['k_per_split'], 'rounds': geo['rounds'], 'base': 0,
                'code_span_words': self.manifest['code_words'], 'scale_base': 0,
                'scale_span_words': self.manifest['scale_words']}
        self.codes, self.scales = L0.Image.matrix(self, meta)
        self.program = [QI.decode_instruction(int(line, 16))
                        for line in (Path(binding) / f'head_program_d{die}.hex').read_text().split()]
        self.descriptors = [QI.decode_descriptor(int(line, 16))
                            for line in (Path(binding) / f'head_segments_d{die}.hex').read_text().split()]
        self.crom = read_crom(Path(binding) / 'head_final_norm_crom.hex')


class HeadMachine(P.Machine):
    def __init__(self, image: HeadImage, die: int, vm, layout):
        self.image = image
        self.lay = FP.LayerZero(None, die, layout)
        self.lay.row0 = die * HEAD_ROWS
        self.vm = vm.copy()
        self.kv = np.zeros(1, dtype=np.float32)
        self.crom = image.crom
        self.argmax, self.logits = None, []
        self.pos = 0

    def me(self, f, dyn):
        if f['me_wsrc']:
            raise ValueError('head has no KV-sourced op')
        n = f['me_nout'] + dyn[f['me_d_nout']]
        row0 = f.get('me_row0', 0)
        split = 1 << f['me_split']
        if split != self.image.manifest['geometry']['split'] or not f['me_round'] or not f['me_amax']:
            raise ValueError('head chunk geometry changed')
        per_round, kc = GROUPS // split, self.image.manifest['geometry']['k_per_split']
        if f['me_wbase'] != row0 // (per_round * W * IL) * kc * IL or f['me_wcs'] != row0 // W:
            raise ValueError('head chunk code/scale base does not match its first row')
        xbase = f['me_xbase'] + dyn[f['me_d_xbase']]
        x = self.vm[xbase:xbase + 4096]
        out = np.empty(n, dtype=np.float32)
        for r in range(0, n, 512):
            e = min(n, r + 512)
            raw = G.matvec(self.image.codes[row0 + r:row0 + e].astype(np.float32), x, split)
            out[r:e] = G.mul(raw, self.image.scales[row0 + r:row0 + e])
        if f['me_oen']:
            raise ValueError('head chunk writes VM')
        self.logits = np.concatenate([self.logits, out]) if f['me_amc'] else out
        # ot_hdc_matvec/core argmax: larger key wins, lower row on equal keys;
        # keys order binary32 with canonical +0 (np.argmax returns the first max).
        self.argmax = int(np.argmax(self.logits))


def run(layer_dirs, head_dirs, binding, preload, out, layers=36):
    if I.SU_WIDTH != 1024 or G.SU_WIDTH != 1024 or G.KV_FMT != 'fp8':
        raise ValueError('oracle requires HDC_SU_WIDTH=1024 and HDC_KV_FMT=fp8')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    x0 = L0._preload_x(preload)
    vms = [np.zeros(L0.VM_ELEMS, dtype=np.float32) for _ in range(TP)]
    for vm in vms:
        vm[VM['X']:VM['X'] + 4096] = x0
    record = {'schema': 'opentallas.qwen-o4-token-tp2-oracle.v1', 'status': 'ISA_golden_only',
              'token': 0, 'position': 0, 'layers': layers, 'tp': TP, 'groups': GROUPS, 'x_preload_sha256': sha(preload),
              'layer_image_sha256': {}, 'layer_x_sha256': {}, 'oracle_source_sha256': {
                  p: sha(ROOT / p) for p in ('tools/qwen_o4_token_oracle.py', 'tools/qwen_o4_layer0_oracle.py',
                                             'tools/hdc_golden.py', 'tools/hdc_program.py', 'tools/hdc_isa.py',
                                             'tools/hdc_qwen_fullshape_isa.py', 'tools/hdc_qwen_fullshape_program.py')}}
    for n in range(layers):
        images = [LayerImage(layer_dirs.format(layer=n, die=d), n) for d in range(TP)]
        if any(im.descriptors != images[0].descriptors for im in images):
            raise ValueError('TP descriptor mismatch')
        vms = run_layer(images, vms)
        record['layer_image_sha256'][f'L{n}'] = [im.manifest['image_sha256'] for im in images]
        for d in range(TP):
            path = out / f'L{n:02d}_die{d}_x.hex'
            L0._bits_hex(path, vms[d][VM['X']:VM['X'] + 4096])
            record['layer_x_sha256'][f'L{n}_die{d}'] = sha(path)
        print(f'layer {n} done', flush=True)
    if layers < 36:
        (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        return record
    heads = []
    with FP.program_geometry(VM):
        for d in range(TP):
            im = HeadImage(head_dirs.format(die=d), binding, d)
            m = HeadMachine(im, d, vms[d], images[0].manifest['matrix_layout'])
            dyn = P.dyn_values(m.lay, token=0, pos=0)
            for f in im.program:
                if f['unit'] == I.UNIT_ME:
                    m.me(f, dyn)
                elif f['unit'] == I.UNIT_SU:
                    m.su(f, dyn)
            heads.append(m)
            path = out / f'head_die{d}_xnorm.hex'
            L0._bits_hex(path, m.vm[8192:8192 + 4096])
            record[f'head_die{d}'] = {'argmax_local': m.argmax, 'row0': d * HEAD_ROWS,
                                      'logit_bits': f'{int(G.bits(np.float32(m.logits[m.argmax]))):08x}',
                                      'rows': len(m.logits), 'xnorm_sha256': sha(path),
                                      'image_sha256': im.manifest['image_sha256']}
    logits = np.concatenate([h.logits for h in heads]).astype(np.float32)
    token = int(np.argmax(logits))
    top2 = np.sort(logits)[-2:]
    record.update({'next_token': token, 'next_logit_bits': f'{int(G.bits(np.float32(logits[token]))):08x}',
                   'top2_margin': float(top2[1] - top2[0]),
                   'claim_boundary': 'Full-token ISA golden (embedding preloaded as in the layer-0 bench); not an RTL verdict.'})
    np.save(out / 'logits.npy', logits)
    (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--layer-dirs', required=True, help='format string with {layer} and {die}')
    ap.add_argument('--head-dirs', required=True, help='format string with {die}')
    ap.add_argument('--binding', type=Path, default=ROOT / 'results/rtl/qwen_o4_fulltoken_binding')
    ap.add_argument('--preload', type=Path, required=True)
    ap.add_argument('--layers', type=int, default=36)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    r = run(args.layer_dirs, args.head_dirs, args.binding, args.preload, args.out, args.layers)
    print(json.dumps({k: r.get(k) for k in ('next_token', 'next_logit_bits', 'top2_margin')}, indent=2))


if __name__ == '__main__':
    main()
