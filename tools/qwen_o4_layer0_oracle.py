#!/usr/bin/env python3
"""ISA arithmetic oracle for one real Qwen3-8B O4 INT8 TP-2 layer.

Consumes the shipped layer-0 code, scale, constant, and program images.  Dense
matrix operations use the golden contiguous K-split reduction; attention and
stream instructions execute the ISA golden.  The two die memories exchange
unscaled FP32 partials in descriptor order; the emitted SU then applies the
single full-row BF16 scale.  This is an ISA oracle, not an RTL verdict.
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

ROOT = Path(__file__).resolve().parents[1]
from hdc_qwen_fullshape_placement import GROUPS, TP  # noqa: E402  (QWEN_O4_GROUPS, QWEN_O4_TP)
W, IL = I.W_LANES, I.INTERLEAVE
VM, VM_ELEMS = FP.vm_map()


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bits_hex(path, values):
    Path(path).write_text(''.join(f'{int(x):08x}\n' for x in G.bits(values)))


def _bf16_u16_to_f32(u16):
    return G.from_bits(np.asarray(u16, dtype=np.uint32) << 16)


class Image:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.manifest = json.loads((self.dir / 'layer0_rom.json').read_text())
        if self.manifest['layer'] != 0 or self.manifest['tp'] != TP:
            raise ValueError('expected emitted layer-0 TP2 images')
        for name, digest in self.manifest['image_sha256'].items():
            if _sha(self.dir / name) != digest:
                raise ValueError(f'image digest mismatch: {name}')
        for name, digest in self.manifest['source_sha256'].items():
            if _sha(ROOT / name) != digest:
                raise ValueError(f'emitter source drift: {name}')
        self.layout = {row['base']: row for row in self.manifest['matrix_layout']}
        self.program = [QI.decode_instruction(int(line, 16)) for line in (self.dir / 'program.hex').read_text().splitlines()]
        self.descriptors = [QI.decode_descriptor(int(line, 16)) for line in (self.dir / 'segments.hex').read_text().splitlines()]
        lo, hi = [], []
        with (self.dir / 'crom.hex').open() as stream:
            for line in stream:
                hi.append(int(line[:8], 16))
                lo.append(int(line[8:16], 16))
        self.crom = np.stack((G.from_bits(np.array(lo, dtype=np.uint32)),
                              G.from_bits(np.array(hi, dtype=np.uint32))), axis=1)

    def matrix(self, meta):
        """Invert the emitter's group/slot/K layout into complete signed rows."""
        groups, n, k, split = GROUPS, meta['rows'], meta['columns'], meta['split']
        per_round, kc, rounds = groups // split, meta['k_per_split'], meta['rounds']
        count = meta['code_span_words']
        word_lanes = groups * W
        buf = np.empty((count, word_lanes), dtype=np.int8)
        with (self.dir / 'matrix_int8.hex').open('rb') as stream:
            for _ in range(meta['base']):
                stream.readline()
            for addr in range(count):
                line = stream.readline().strip()
                if len(line) != 2 * word_lanes:
                    raise ValueError(f'short matrix word {meta["name"]}:{addr}')
                buf[addr] = np.frombuffer(bytes.fromhex(line.decode()), dtype=np.int8)[::-1]
        codes = (buf.reshape(rounds, kc, IL, per_round, split, W)
                 .transpose(0, 3, 2, 5, 4, 1)
                 .reshape(rounds * per_round * IL * W, k)[:n].copy())
        if meta['name'] in ('o', 'down'):
            base = self.manifest['post_tp_scale_bases'][0 if meta['name'] == 'o' else 1]
            scales = self.crom[base:base+n, 0].copy()
        else:
            count = meta['scale_span_words']
            slots = np.empty((count, W), dtype=np.uint16)
            with (self.dir / 'matrix_scale_bf16.hex').open('rb') as stream:
                for _ in range(meta['scale_base']):
                    stream.readline()
                for addr in range(count):
                    line = stream.readline().strip()
                    slots[addr] = np.frombuffer(bytes.fromhex(line.decode()), dtype='>u2')[::-1]
            scales = _bf16_u16_to_f32(slots.reshape(-1)[:n])
        return codes, scales


class DieMachine(P.Machine):
    def __init__(self, image: Image):
        self.image = image
        self.lay = FP.LayerZero(None, image.manifest['die'], image.manifest['matrix_layout'])
        self.vm = np.zeros(VM_ELEMS, dtype=np.float32)
        self.kv = np.zeros(2 * self.lay.kv_v0, dtype=np.float32)
        self.crom = image.crom
        self.argmax, self.logits = None, []
        self.pos = 0

    def me(self, f, dyn):
        if f['me_wsrc']:
            return super().me(f, dyn)
        meta = self.image.layout[f['me_wbase']]
        n = f['me_nout'] + dyn[f['me_d_nout']]
        split = 1 << f['me_split']
        if n != meta['rows'] or split != meta['split']:
            raise ValueError(f'ISA/matrix geometry mismatch: {meta["name"]}')
        codes, scales = self.image.matrix(meta)
        xbase = f['me_xbase'] + dyn[f['me_d_xbase']]
        k = meta['columns']
        x = self.vm[xbase:xbase+k]
        out = np.empty(n, dtype=np.float32)
        for row in range(0, n, 256):
            end = min(n, row + 256)
            raw = G.matvec(codes[row:end].astype(np.float32), x, split)
            out[row:end] = raw if meta['name'] in ('o', 'down') else G.mul(raw, scales[row:end])
        if not f['me_oen']:
            raise ValueError('first-layer oracle expects each matrix to write VM')
        self.vm[f['me_obase'] * W:f['me_obase'] * W+n] = out


def _preload_x(path):
    rows = [line.strip() for line in Path(path).read_text().splitlines()]
    if not rows or rows[0].lower() != '@1000' or len(rows) != 4097:
        raise ValueError('expected token-0 X preload at VM element 4096')
    return G.from_bits(np.array([int(s, 16) for s in rows[1:]], dtype=np.uint32))


def run(image_dirs, preload, out):
    if I.SU_WIDTH != 1024 or G.SU_WIDTH != 1024 or G.KV_FMT != 'fp8':
        raise ValueError('oracle requires HDC_SU_WIDTH=1024 and HDC_KV_FMT=fp8')
    images = [Image(d) for d in image_dirs]
    if [x.manifest['die'] for x in images] != [0, 1]:
        raise ValueError('image order must be die 0 then die 1')
    if images[0].descriptors != images[1].descriptors:
        raise ValueError('TP2 descriptor mismatch')
    machines = [DieMachine(im) for im in images]
    x0 = _preload_x(preload)
    for mach in machines:
        mach.vm[VM['X']:VM['X']+4096] = x0
    traces = [dict() for _ in machines]
    with FP.program_geometry(VM):
        dyns = [P.dyn_values(m.lay, token=0, pos=0) for m in machines]
        desc = images[0].descriptors
        for idx, seg in enumerate(desc):
            first = seg['program_base']
            end = desc[idx+1]['program_base'] if idx+1 < len(desc) else len(images[0].program)
            for d, (mach, image, dyn) in enumerate(zip(machines, images, dyns)):
                for pc in range(first, end):
                    f = image.program[pc]
                    if f['unit'] == I.UNIT_ME:
                        mach.me(f, dyn)
                    elif f['unit'] == I.UNIT_SU:
                        mach.su(f, dyn)
                    if pc in (10, 21, 30, 31):
                        traces[d][f'pc{pc}'] = mach.vm.copy() if pc != 10 else mach.kv.copy()
            if seg['kind'] == P.COLL_ALLREDUCE:
                lo, hi = seg['vm_word'] * W, (seg['vm_word'] + seg['words']) * W
                summed = G.fold([m.vm[lo:hi].copy() for m in machines])
                for mach in machines:
                    mach.vm[lo:hi] = summed
            elif seg['kind'] != P.COLL_END:
                raise ValueError('unexpected first-layer collective')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    result = {'schema': 'opentallas.qwen-o4-layer0-tp2-oracle.v1', 'status': 'ISA_golden_only',
              'token': 0, 'position': 0, 'emitter_basis_commit': '7ed6bb26',
              'emitter_source_sha256': images[0].manifest['source_sha256'],
              'arithmetic': {'groups_per_die': GROUPS, 'su_width': G.SU_WIDTH,
                             'kv_format': G.KV_FMT, 'weight_format': 'signed-int8-per-row-bf16-scale'},
              'oracle_source_sha256': {p: _sha(ROOT / p) for p in
                                        ('tools/qwen_o4_layer0_oracle.py', 'tools/hdc_golden.py',
                                         'tools/hdc_program.py', 'tools/hdc_isa.py',
                                         'tools/hdc_qwen_fullshape_isa.py')},
              'x_preload_sha256': _sha(preload), 'input_image_sha256': {}, 'outputs': {},
              'claim_boundary': 'One shipped layer0 ISA golden trace, not an RTL bit-exact gate or chip throughput.'}
    for d, (mach, image, trace) in enumerate(zip(machines, images, traces)):
        result['input_image_sha256'][f'die{d}'] = image.manifest['image_sha256']
        krow = np.array([mach.kv[mach.lay.k_elem(0, g, 0, dim)] for g in range(4) for dim in range(128)], dtype=np.float32)
        vrow = np.array([mach.kv[mach.lay.v_elem(0, g, 0, dim)] for g in range(4) for dim in range(128)], dtype=np.float32)
        vectors = {'x_initial': x0, 't1_after_o_scale': trace['pc21'][VM['T1']:VM['T1']+4096],
                   't1_after_down_scale': trace['pc30'][VM['T1']:VM['T1']+4096],
                   'x_final': trace['pc31'][VM['X']:VM['X']+4096],
                   'k_pos0': krow, 'v_pos0': vrow}
        result['outputs'][f'die{d}'] = {}
        for name, vector in vectors.items():
            path = out / f'die{d}_{name}.hex'
            _bits_hex(path, vector)
            result['outputs'][f'die{d}'][name] = {'elements': len(vector), 'sha256': _sha(path),
                                                  'nonzero': int(np.count_nonzero(vector))}
    (out / 'oracle.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die0', type=Path, required=True)
    ap.add_argument('--die1', type=Path, required=True)
    ap.add_argument('--preload', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(run((args.die0, args.die1), args.preload, args.out), indent=2))


if __name__ == '__main__':
    main()
