#!/usr/bin/env python3
"""Build serial TP4 DSpark ROM/ISA inputs for the combined Qwen runtime.

This is checkpoint quantisation and image packing, never model inference.
The source checkpoint is read once per matrix; one process loops over ranks.
Only published W8 rows are used, without norm folding. Per-stage image addresses
are local; field_offset records their placement after the target's 20,016 words.
The system owner must bind that placement to its real field bank selects.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('QWEN_O4_TP', '4')
os.environ.setdefault('HDC_SU_WIDTH', '64')

import numpy as np
import torch
from safetensors import safe_open

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as QI
import hdc_qwen_fullshape_program_w12 as FP
from hdc_qwen_fullshape_placement_w12 import GROUPS, TP, matrix
from hdc_qwen_layer0_rom_w12 import joined_matrices, matrix_plan, engine_word_arrays, word_hex
from qwen3_deployment_quality import quantize_w8
from qwen_rom_dspark_draft_isa import encode_layer, freeze_dyn
import qwen_rom_verify_program_w12 as V

REVISION = '03326e5043815da1f81b109078b2889737c26017'
CHECKPOINT_SHA256 = '5c922d1f96c8d18dbdf005c40ea99878d9133d70eaa3be4bd1077ee5f2afc1e5'
ROOT = Path(__file__).resolve().parents[1]


def encode_program(program):
    words, desc = [], []
    for instructions, (kind, base, count, row0) in P.segments(program):
        desc.append(V.encode_descriptor(kind, base, count, len(words), row0))
        words.extend(QI.encode_instruction(f) for f in instructions)
    if len(words) > 1024 or len(desc) > 64:
        raise ValueError('serial stage exceeds companion program memory')
    return words, desc


def write_program(directory, prefix, encoded):
    words, desc = encoded
    (directory / f'{prefix}program.hex').write_text(''.join(f'{w:0256x}\n' for w in words))
    (directory / f'{prefix}segments.hex').write_text(''.join(f'{w:016x}\n' for w in desc))


def context_kv_program(lay, position, *, enabled=False):
    """Ingest one actual hidden_norm(FC(features)) vector from VM H.

    The released drafter projects context directly, without input RMSNorm.
    Reuse the exact layer QKV-through-K/V instructions, starting at QKV and
    ending before scores. Q computations are retained to keep existing order.
    The caller fences these writes before starting the speculative block.
    """
    if not enabled or lay.norm_fold or not 0 <= position < FP.TMAX:
        raise ValueError('requires enabled explicit-norm context ingest and valid position')
    vm, _ = FP.vm_map()
    with FP.program_geometry(vm):
        program = P.build_program(lay, layers=[0], embed=False, head=False, scale_bases=True)
    begin = next(i for i, f in enumerate(program) if f['unit'] == I.UNIT_ME)
    end = next(i for i in range(begin+1, len(program)) if program[i]['unit'] == I.UNIT_ME)
    out = [freeze_dyn(f, lay, position, position+1) for f in program[begin:end]]
    out.append(dict(unit=I.UNIT_END, barrier=1, chase=0, _coll=(P.COLL_END, 0, 0, 0)))
    return out


def projection_program(lay, row, input_base, output_base, *, enabled=False):
    """Existing W12 row projection into VM, with no reduction or argmax.

    Used for FC and Markov W2. FC's actual all-gather and hidden norm belong
    between this stage and context ingest; W2 must feed biased stream argmax.
    Neither operation may be replaced by an all-reduce/ME argmax shortcut.
    """
    if not enabled or min(input_base, output_base) < 0 or output_base % I.W_LANES:
        raise ValueError('requires enabled aligned projection addresses')
    proxy = copy.copy(lay)
    proxy.mat = {('lm_head', 1, 1): {'base': row['base'], 'n': row['rows'],
                 'k': row['k_per_split'], 'tiles': row['rounds'],
                 'split': row['split'], 'scale_base': row['scale_base']}}
    vm, _ = FP.vm_map()
    with FP.program_geometry(vm):
        program = P.build_program(proxy, layers=[], embed=False, head=(1, 1),
                                  wchunk=512, scale_bases=True)
    for f in program:
        f.update(barrier=1, chase=0, chase_n=0, wait_me=0, wait_su=0)
        if f['unit'] == I.UNIT_ME:
            f.update(me_xbase=input_base, me_obase=f['me_obase'] + output_base // I.W_LANES,
                     me_oen=1, me_amax=0, me_amc=0, me_row0=0)
        elif f['unit'] == I.UNIT_END:
            f['_coll'] = (P.COLL_END, 0, 0, 0)
        else:
            raise ValueError('unexpected non-matrix projection instruction')
    return program


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def split_rows(codes, scales, rank, axis):
    if rank not in range(4) or axis not in ('rows', 'columns'):
        raise ValueError('invalid TP4 rank or matrix shard axis')
    if codes.shape[0 if axis == 'rows' else 1] % 4:
        raise ValueError('matrix is not evenly shardable across four ranks')
    if axis == 'rows':
        n = len(codes) // 4
        return codes[rank*n:(rank+1)*n], scales[rank*n:(rank+1)*n]
    k = codes.shape[1] // 4
    return codes[:, rank*k:(rank+1)*k].contiguous(), scales


def write_matrix_images(directory, matrices, rows):
    """Separate compact code and scale address spaces of the current W12 core."""
    scale_depth = max(row['scale_base'] + (row['rounds']-1) * (GROUPS // row['split']) * I.INTERLEAVE
                      + GROUPS * I.INTERLEAVE for row in rows)
    written_scales = 0
    with (directory / 'matrix_int8.hex').open('w') as cf, (directory / 'matrix_scale_bf16.hex').open('w') as sf:
        for row in rows:
            codes, scales = matrices[row['name']]
            for address, (code, scale) in enumerate(engine_word_arrays(
                    codes, scales, split=row['split'], raw_partial=row['name'] in ('o', 'down'))):
                if address < row['code_span_words']:
                    cf.write(word_hex(code, 8) + '\n')
                if address < row['scale_span_words']:
                    sf.write(word_hex(scale, 16) + '\n')
                    written_scales += 1
        for _ in range(written_scales, scale_depth):
            sf.write('3f80' * I.W_LANES + '\n')
    return scale_depth


def constants(norms, matrices, lay):
    cb = lay.cb
    data = np.zeros((cb['rope'] + FP.TMAX * lay.half, 2), dtype=np.float32)
    for name in ('in', 'post'):
        base = cb[0, name]
        data[base:base+lay.H, 0] = norms[name]
    qk = np.concatenate((np.tile(norms['qn'], lay.NH), np.tile(norms['kn'], lay.KV)))
    data[cb[0, 'qk']:cb[0, 'qk'] + len(qk), 0] = qk
    data[cb['qscale'], 1] = np.float32(1 / np.sqrt(lay.HD))
    for position in range(FP.TMAX):
        cos, sin, _ = G.rope_tables(position, lay.HD, 1_000_000)
        base = cb['rope'] + position * lay.half
        data[base:base+lay.half] = np.stack((cos, sin), axis=1)
    scales = [np.asarray(matrices[n][1], dtype=np.uint32) << 16 for n in ('o', 'down')]
    bases = [len(data), len(data) + lay.H]
    tail = np.zeros((2 * lay.H, 2), dtype=np.float32)
    tail[:, 0] = np.concatenate(scales).view(np.float32)
    return np.concatenate((data, tail)), bases


def emit(snapshot, out, start, slots, *, enabled=False, threads=4):
    if not enabled:
        raise ValueError('DSpark image/program successor is default-off')
    if slots not in (3, 7) or start < 0 or start + slots > FP.TMAX or threads < 1:
        raise ValueError('invalid drafter block or packing thread count')
    if TP != 4 or GROUPS != 6144 or I.SU_WIDTH != 64:
        raise ValueError('requires the actual TP4 G6144 SU64 geometry')
    if snapshot.name != REVISION:
        raise ValueError('drafter checkpoint revision mismatch')
    cfg = json.loads((snapshot / 'config.json').read_text())
    if (cfg['hidden_size'], cfg['num_hidden_layers'], cfg['num_attention_heads'],
            cfg['num_key_value_heads'], cfg['head_dim'], cfg['intermediate_size']) != (4096, 5, 32, 8, 128, 12288):
        raise ValueError('not the pinned DSpark drafter shape')
    checkpoint_sha256 = digest(snapshot / 'model.safetensors')
    if checkpoint_sha256 != CHECKPOINT_SHA256:
        raise ValueError('released checkpoint payload SHA256 mismatch')
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(threads)
    stages, pieces = [], []
    offset = 20016
    with safe_open(str(snapshot / 'model.safetensors'), framework='pt', device='cpu') as sf:
        def quant(name):
            q, s, _ = quantize_w8(sf.get_tensor(name).float())
            return q, s
        fc = quant('fc.weight')
        pieces.extend(write_piece(out, 'fc', fc, 'rows', offset))
        offset += matrix(0, 'fc', 1024, 20480)['words']
        del fc
        for layer in range(5):
            prefix = f'layers.{layer}.'
            spec = {'q': ('self_attn.q_proj', 'rows'), 'k': ('self_attn.k_proj', 'rows'),
                    'v': ('self_attn.v_proj', 'rows'), 'o': ('self_attn.o_proj', 'columns'),
                    'gate': ('mlp.gate_proj', 'rows'), 'up': ('mlp.up_proj', 'rows'),
                    'down': ('mlp.down_proj', 'columns')}
            quantized = {name: quant(prefix + suffix + '.weight') for name, (suffix, _) in spec.items()}
            norms = {short: sf.get_tensor(prefix + name + '.weight').float().numpy()
                     for short, name in [('in', 'input_layernorm'), ('post', 'post_attention_layernorm'),
                                         ('qn', 'self_attn.q_norm'), ('kn', 'self_attn.k_norm')]}
            dirs = []
            for rank in range(4):
                source = {}
                for name, (_, axis) in spec.items():
                    q, s = split_rows(*quantized[name], rank, axis)
                    source[name] = {'codes': q, 'scales': s}
                matrices = joined_matrices(source)
                rows = matrix_plan(matrices, compact_banks=True)
                directory = out / f'D{layer}-d{rank}'
                directory.mkdir()
                lay = FP.LayerZero(None, rank, rows)
                lay.norm_fold = False
                crom, post_scales = constants(norms, matrices, lay)
                scale_depth = write_matrix_images(directory, matrices, rows)
                (directory / 'crom.hex').write_text(P.hexwords(((int(G.bits(hi)) << 32) | int(G.bits(lo))
                    for lo, hi in crom), 64))
                program, desc = encode_layer(lay, slots, start, post_scales, enabled=True)
                write_program(directory, '', (program, desc))
                # Actual context position is bound by the runtime; this is the
                # first nonzero-context row, not a fabricated feature vector.
                if start:
                    write_program(directory, 'context_', encode_program(
                        context_kv_program(lay, start-1, enabled=True)))
                manifest = {'layer': layer, 'die': rank, 'tp': 4, 'norm_fold': False,
                            'context_program_position': start-1 if start else None,
                            'context_input_vm_base': FP.vm_map()[0]['H'],
                            'field_offset': offset, 'matrix_layout': rows,
                            'post_tp_scale_bases': post_scales, 'scale_rom_words': scale_depth,
                            'program_words': len(program), 'segments': len(desc)}
                (directory / 'drafter_layer.json').write_text(json.dumps(manifest, indent=1)+'\n')
                dirs.append(str(directory.resolve()))
            offset += rows[-1]['end']
            stages.append(' '.join([f'D{layer}', *dirs, '0']))
            print(f'layer {layer} packed four ranks; field end {offset}', flush=True)
            del quantized, source, matrices
        w2 = quant('markov_head.markov_w2.weight')
        pieces.extend(write_piece(out, 'markov_w2', w2, 'rows', offset))
        offset += matrix(0, 'markov_w2', 37984, 256)['words']
        # Markov w1 row lookup is replicated at the existing IO edge.
        q, s = quant('markov_head.markov_w1.weight')
        np.save(out / 'markov_w1_codes.npy', q.numpy())
        np.save(out / 'markov_w1_scales_bf16.npy', s.view(torch.int16).numpy().view(np.uint16))
        for name in ('hidden_norm', 'norm'):
            np.save(out / f'{name}.npy', sf.get_tensor(name+'.weight').float().numpy())
    if offset > 6 * 4096:
        raise ValueError(f'drafter does not fit the accepted six-bank tile: {offset} words')
    (out / 'stages.txt').write_text('\n'.join(stages)+'\n')
    manifest = {'schema': 'opentallas.qwen-rom-dspark-images.v1', 'status': 'IMAGES_AND_LAYER_ISA_ONLY',
                'checkpoint': REVISION, 'start': start, 'slots': slots, 'torch_version': torch.__version__,
                'field_end_words': offset, 'tile_banks': 6, 'pieces': pieces,
                'checkpoint_sha256': checkpoint_sha256,
                'source_sha256': {name: digest(ROOT/name) for name in (
                    'tools/qwen_rom_dspark_images.py', 'tools/qwen_rom_dspark_draft_isa.py',
                    'tools/hdc_qwen_layer0_rom_w12.py', 'tools/hdc_qwen_int8_image_w12.py',
                    'tools/qwen3_deployment_quality.py', 'tools/hdc_program.py', 'tools/hdc_isa.py',
                    'tools/hdc_qwen_fullshape_placement_w12.py', 'tools/hdc_qwen_fullshape_program_w12.py',
                    'tools/hdc_golden.py', 'tools/hdc_qwen_fullshape_isa_w12.py',
                    'tools/qwen_rom_verify_program_w12.py')},
                'integration_needed': ['FC all-gather and hidden_norm', 'shared target embedding and head',
                    'biased Markov stream argmax', 'target feature exports', 'actual serial loop backend'],
                'claim_boundary': 'Real ROM input payload and serial layer programs; no inference, RTL exactness, composed latency or SS/FF verdict.'}
    (out / 'drafter_images.json').write_text(json.dumps(manifest, indent=1)+'\n')
    return manifest


def write_piece(out, name, quantized, axis, offset):
    pieces = []
    for rank in range(4):
        q, s = split_rows(*quantized, rank, axis)
        codes, scales = q.numpy(), s.view(torch.int16).numpy().view(np.uint16).reshape(-1)
        row = matrix(0, name, *codes.shape)
        row.update(scale_base=0, code_span_words=row['words'],
                   scale_span_words=row['rounds'] * (GROUPS // row['split']) * I.INTERLEAVE)
        directory = out / f'{name}-d{rank}'
        directory.mkdir()
        write_matrix_images(directory, {name: (codes, scales)}, [row])
        # No model execution: only existing ME instructions and companion END.
        lay = FP.LayerZero(None, rank, [row] * 4)
        write_program(directory, '', encode_program(projection_program(
            lay, row, 0, 32768, enabled=True)))
        pieces.append({'name': name, 'rank': rank, 'field_offset': offset, 'matrix': row,
                       'input_vm_base': 0, 'output_vm_base': 32768,
                       'directory': str(directory.resolve())})
    return pieces


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--slots', type=int, choices=(3, 7), default=3)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--enable', action='store_true')
    a = ap.parse_args()
    result = emit(a.snapshot, a.out, a.start, a.slots, enabled=a.enable, threads=a.threads)
    print(json.dumps({k: result[k] for k in ('status', 'field_end_words', 'tile_banks')}))


if __name__ == '__main__':
    main()
