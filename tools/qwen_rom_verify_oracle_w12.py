#!/usr/bin/env python3
"""ISA golden for the p-position verify layer: p sequential AR decodes vs one verify program.

Reference (AR): the pinned TP4 layer programs (img_tp4 program.hex/segments.hex,
the ones tools/qwen_o4_token_oracle_w12.py runs for the retained terminal) are
executed on the ISA golden (qwen_o4_layer0_oracle_w12.DieMachine: dense matrices
by the golden contiguous K-split reduction, stream/attention instructions by
the hdc_golden arithmetic, all-reduce by hdc_golden.fold in rank order) once per
position, positions pos0 .. pos0+p-1 in order, each layer's KV window carried
from position to position -- i.e. autoregressive decoding of the token block.

Verify: the p-position program of tools/qwen_rom_verify_program_w12.py, run once
per layer on the same golden, its instruction POS_OFF selecting pos0 + j for the
DYN rows.

Writes, per layer and die, every position's X (the RTL comparison targets) and a
record of AR == verify for every position, layer and die.  Not an RTL verdict.

  HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 \\
  qwen_rom_verify_oracle_w12.py --img-dirs '/home/ubuntu/w12/img_tp4/L{layer}-d{die}' \\
      --verify-stages VDIR/stages.txt --tokens 0,50994 --preload-dir PDIR --layers 2 --out OUT
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as QI
import qwen_o4_layer0_oracle_w12 as L0
import qwen_o4_token_oracle_w12 as TO
import qwen_rom_verify_program_w12 as V

ROOT = Path(__file__).resolve().parents[1]
W, TP = L0.W, L0.TP
VM1 = L0.VM


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


# one decode of a matrix per (image, base): the ISA golden re-reads the hex per op otherwise
_matrix = L0.Image.matrix


@functools.lru_cache(maxsize=None)
def _matrix_cached(image, base):
    return _matrix(image, image.layout[base])


def _matrix_by_meta(self, meta):
    layout = getattr(self, 'layout', None)
    if layout is not None and meta.get('base') in layout and layout[meta['base']] is meta:
        return _matrix_cached(self, meta['base'])
    return _matrix(self, meta)


L0.Image.matrix = _matrix_by_meta


class LayerImage(TO.LayerImage):
    """TO.LayerImage whose image digests are verified but whose EMITTER source pins
    may have drifted since the images were emitted (they pin the emitter, not
    the arithmetic); the drift is recorded, not hidden."""

    drift = {}

    def __init__(self, directory, layer):
        self.dir = Path(directory)
        self.manifest = json.loads((self.dir / f'layer{layer}_rom.json').read_text())
        if self.manifest['layer'] != layer or self.manifest['tp'] != TP:
            raise ValueError(f'expected layer {layer} TP images in {directory}')
        for name, digest in self.manifest['image_sha256'].items():
            if sha(self.dir / name) != digest:
                raise ValueError(f'image digest mismatch: {directory}/{name}')
        for name, digest in self.manifest['source_sha256'].items():
            if sha(ROOT / name) != digest:
                LayerImage.drift[name] = {'image_pin': digest, 'head': sha(ROOT / name)}
        self.layout = {row['base']: row for row in self.manifest['matrix_layout']}
        self.program = [QI.decode_instruction(int(line, 16)) for line in (self.dir / 'program.hex').read_text().splitlines()]
        self.descriptors = [QI.decode_descriptor(int(line, 16)) for line in (self.dir / 'segments.hex').read_text().splitlines()]
        self.crom = TO.read_crom(self.dir / 'crom.hex')


class VerifyImage(LayerImage):
    """A layer image whose program/segments come from the verify stage dir."""

    def __init__(self, img_dir, layer, verify_dir):
        super().__init__(img_dir, layer)
        words = [int(x, 16) for x in (Path(verify_dir) / 'program.hex').read_text().split()]
        self.program = [QI.decode_instruction(w) for w in words]
        self.pos_off = [V.decode_pos_off(w) for w in words]
        self.descriptors = [V.decode_descriptor(int(x, 16)) for x in (Path(verify_dir) / 'segments.hex').read_text().split()]
        self.verify_dir = Path(verify_dir)


def run_program(machines, images, pos_of, vm_elems=None):
    """Run one layer program on the TP machines; pos_of(pc) gives the DYN position."""
    desc = images[0].descriptors
    for idx, seg in enumerate(desc):
        first = seg['program_base']
        end = desc[idx + 1]['program_base'] if idx + 1 < len(desc) else len(images[0].program)
        for mach, image in zip(machines, images):
            for pc in range(first, end):
                f = image.program[pc]
                pos = pos_of(image, pc)
                mach.pos = pos
                dyn = P.dyn_values(mach.lay, token=0, pos=pos)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--img-dirs', required=True, help="format string, {layer} {die}: pinned img_tp4 layer dirs")
    ap.add_argument('--verify-stages', type=Path, required=True)
    ap.add_argument('--tokens', required=True, help='comma list: the block tokens at pos0 ..')
    ap.add_argument('--pos0', type=int, default=0)
    ap.add_argument('--preload-dir', type=Path, required=True, help='holds tok{t}/vm_x_fp32.hex per token')
    ap.add_argument('--layers', type=int, default=1)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if I.SU_WIDTH != 1024 or G.SU_WIDTH != 1024 or G.KV_FMT != 'fp8':
        raise SystemExit('oracle requires HDC_SU_WIDTH=1024 and HDC_KV_FMT=fp8')
    if a.pos0 != 0:
        raise SystemExit('pos0 > 0 needs a prefilled KV window; this gate decodes the block from position 0')
    tokens = [int(t) for t in a.tokens.split(',')]
    p = len(tokens)
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    vstages = {ln.split()[0]: ln.split()[1:-1] for ln in a.verify_stages.read_text().splitlines() if ln.strip()}
    vrec = json.loads((a.verify_stages.parent / 'verify_images.json').read_text())
    if vrec['p'] != p:
        raise SystemExit(f"verify images are p={vrec['p']}, tokens give p={p}")
    x_bases = vrec['stages'][0]['x_bases']
    vm_elems = vrec['stages'][0]['vm_elems']
    x0 = [L0._preload_x(a.preload_dir / f'tok{t}' / 'vm_x_fp32.hex') for t in tokens]
    record = {'schema': 'opentallas.qwen-rom-verify-oracle.v1', 'status': 'ISA_golden_only', 'p': p,
              'tokens': tokens, 'pos0': a.pos0, 'layers': a.layers, 'x_bases': x_bases,
              'preload_sha256': {t: sha(a.preload_dir / f'tok{t}' / 'vm_x_fp32.hex') for t in tokens},
              'source_sha256': {q: sha(ROOT / q) for q in (
                  'tools/qwen_rom_verify_oracle_w12.py', 'tools/qwen_rom_verify_program_w12.py',
                  'tools/qwen_o4_token_oracle_w12.py', 'tools/qwen_o4_layer0_oracle_w12.py', 'tools/hdc_golden.py',
                  'tools/hdc_program.py', 'tools/hdc_isa.py', 'tools/hdc_qwen_fullshape_isa_w12.py',
                  'tools/hdc_qwen_fullshape_program_w12.py')},
              'layer': {}}
    ar_x = [x.copy() for x in x0]          # per position, identical across dies after each all-reduce
    vf_vm = None
    all_equal = True
    with __import__('hdc_qwen_fullshape_program_w12').program_geometry(VM1):
        for n in range(a.layers):
            images = [LayerImage(a.img_dirs.format(layer=n, die=d), n) for d in range(TP)]
            # --- AR reference: positions in order, KV window carried
            ar_m = [L0.DieMachine(im) for im in images]
            ar_out = []
            for j in range(p):
                for m in ar_m:
                    m.vm[VM1['X']:VM1['X'] + 4096] = ar_x[j]
                run_program(ar_m, images, lambda im, pc, j=j: a.pos0 + j)
                xs = [m.vm[VM1['X']:VM1['X'] + 4096].copy() for m in ar_m]
                if any(not np.array_equal(G.bits(xs[0]), G.bits(x)) for x in xs[1:]):
                    raise SystemExit(f'AR dies disagree at layer {n} position {j}')
                ar_out.append(xs[0])
            # --- verify program: one run over the block
            vimages = [VerifyImage(a.img_dirs.format(layer=n, die=d), n, vstages[f'L{n}'][d]) for d in range(TP)]
            vf_m = []
            for im in vimages:
                m = L0.DieMachine(im)
                m.vm = np.zeros(vm_elems, dtype=np.float32)
                vf_m.append(m)
            for m in vf_m:
                for j in range(p):
                    src = x0[j] if n == 0 else vf_vm[j]
                    m.vm[x_bases[j]:x_bases[j] + 4096] = src
            run_program(vf_m, vimages, lambda im, pc: a.pos0 + im.pos_off[pc])
            vf_vm = [vf_m[0].vm[x_bases[j]:x_bases[j] + 4096].copy() for j in range(p)]
            lrec = {}
            for j in range(p):
                eq_dies = all(np.array_equal(G.bits(vf_m[d].vm[x_bases[j]:x_bases[j] + 4096]), G.bits(ar_out[j]))
                              for d in range(TP))
                all_equal &= eq_dies
                for d in range(TP):
                    path = out / f'L{n:02d}_p{j}_die{d}_x.hex'
                    L0._bits_hex(path, ar_out[j])
                lrec[f'pos{a.pos0 + j}'] = {'token': tokens[j], 'verify_equals_ar_all_dies': bool(eq_dies),
                                           'x_sha256': sha(out / f'L{n:02d}_p{j}_die0_x.hex')}
            record['layer'][f'L{n}'] = lrec
            record.setdefault('verify_program_sha256', {})[f'L{n}'] = [sha(Path(vstages[f'L{n}'][d]) / 'program.hex') for d in range(TP)]
            ar_x = ar_out
            print(f'layer {n}: ' + ' '.join(f"pos{a.pos0 + j}={'EQ' if lrec[f'pos{a.pos0 + j}']['verify_equals_ar_all_dies'] else 'DIFF'}" for j in range(p)), flush=True)
    record['emitter_source_drift'] = LayerImage.drift
    record['verify_equals_ar'] = bool(all_equal)
    (out / 'oracle.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'verify_equals_ar': all_equal, 'p': p}))
    if not all_equal:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
