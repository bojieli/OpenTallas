#!/usr/bin/env python3
"""Bind every shipped Qwen3-8B TP2 stage to compact INT8 image/ISA contracts.

This is a source and address preflight. It emits small stage programs and a
36-layer image plan without allocating checkpoint-sized matrix payloads.
"""
from contextlib import ExitStack
import argparse
import hashlib
import json
from pathlib import Path

from safetensors import safe_open

import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as QI
import hdc_qwen_fullshape_program_w12 as FP
from hdc_qwen_fullshape_placement_w12 import CONFIG, LOCK, GROUPS, TP, matrix
from hdc_qwen_layer0_rom_w12 import pinned_snapshot

ROOT = Path(__file__).resolve().parents[1]
# Compact per-layer code/scale words at the die's group count (QWEN_O4_GROUPS)
# Published (G, TP) geometries are pinned; other design points are derived and recorded.
PINNED = {(6144, 2): (992, 1488, 11, 7), (5120, 2): (1248, 1560, 12, 8)}
HEAD_ROWS = 151936 // TP
LAYER_CROM_WORDS = 543233
# constants: 2H norm rows + (NH + KV)*HD q/k norms + qscale, then TMAX x HD/2 RoPE pairs, then the post-TP
# o and down scales (hdc_qwen_layer0_rom_w12.constant_words); (535041, 539137) at TP2
_ROPE = 2 * 4096 + (32 // TP + 8 // TP) * 128 + 1
POST_SCALE_BASES = (_ROPE + FP.TMAX * 64, _ROPE + FP.TMAX * 64 + 4096)
assert TP != 2 or POST_SCALE_BASES == (535041, 539137)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compact_rows():
    shapes = [('qkv', (32 // TP + 2 * 8 // TP) * 128, 4096), ('o', 4096, 32 // TP * 128),
              ('gu', 2 * 12288 // TP, 4096), ('down', 4096, 12288 // TP)]
    rows, code_base, scale_base = [], 0, 0
    for name, n, k in shapes:
        row = matrix(code_base, name, n, k)
        row['scale_base'] = scale_base
        row['scale_span_words'] = row['rounds'] * (GROUPS // row['split']) * I.INTERLEAVE
        row['code_span_words'] = row['words']
        code_base = row['end']
        scale_base += row['scale_span_words']
        rows.append(row)
    pin = PINNED.get((GROUPS, TP))
    if pin and (code_base, scale_base) != pin[:2]:
        raise ValueError('compact layer address geometry changed')
    return rows


def source_shapes(snapshot):
    """Check all source tensor shapes/dtypes via safetensors metadata only."""
    index = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    expected = {}
    for layer in range(36):
        p = f'model.layers.{layer}.'
        expected.update({p + key: shape for key, shape in {
            'input_layernorm.weight': (4096,), 'post_attention_layernorm.weight': (4096,),
            'self_attn.q_norm.weight': (128,), 'self_attn.k_norm.weight': (128,),
            'self_attn.q_proj.weight': (4096, 4096),
            'self_attn.k_proj.weight': (1024, 4096),
            'self_attn.v_proj.weight': (1024, 4096),
            'self_attn.o_proj.weight': (4096, 4096),
            'mlp.gate_proj.weight': (12288, 4096),
            'mlp.up_proj.weight': (12288, 4096),
            'mlp.down_proj.weight': (4096, 12288)}.items()})
    expected.update({'model.embed_tokens.weight': (151936, 4096),
                     'lm_head.weight': (151936, 4096), 'model.norm.weight': (4096,)})
    with ExitStack() as stack:
        files = {filename: stack.enter_context(safe_open(str(snapshot / filename), framework='pt', device='cpu'))
                 for filename in set(index[name] for name in expected)}
        for name, shape in expected.items():
            entry = files[index[name]].get_slice(name)
            if tuple(entry.get_shape()) != shape or entry.get_dtype() != 'BF16':
                raise ValueError(f'shipped tensor shape/dtype mismatch: {name}')
    return len(expected)


def write_hex(out, stem, words, width):
    path = out / f'{stem}.hex'
    path.write_text(''.join(f'{int(word):0{width // 4}x}\n' for word in words))
    return path


def write_final_norm(snapshot, out):
    """Emit the small head-stage CROM image at the program's base zero."""
    index = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    name = 'model.norm.weight'
    with safe_open(str(snapshot / index[name]), framework='pt', device='cpu') as sf:
        norm = sf.get_tensor(name).float().numpy().view('uint32')
    if norm.shape != (4096,):
        raise ValueError('final norm length changed')
    return write_hex(out, 'head_final_norm_crom', (int(bit) for bit in norm), 64)


def check_stage_isa(embed_words, embed_desc, layer, heads, rows):
    """Reject silent truncation or a return to code-base-derived scale reads."""
    embed = [QI.decode_instruction(word) for word in embed_words]
    if len(embed) != 2 or embed[0]['a_d'] != I.DYN_EMBED or embed[0]['a_base'] != 0:
        raise ValueError('embedding token address schedule changed')
    if len(embed_desc) != 1 or QI.decode_descriptor(embed_desc[0])['kind'] != P.COLL_END:
        raise ValueError('embedding stage descriptor changed')
    instructions = [QI.decode_instruction(int(word, 16)) for word in layer['program_hex']]
    mes = [item for item in instructions if item['unit'] == I.UNIT_ME and not item['me_wsrc']]
    for row in rows:
        if not any(item['me_wbase'] == row['base'] and item['me_wcs'] == row['scale_base']
                   for item in mes):
            raise ValueError(f"independent code/scale base absent for {row['name']}")
    if layer['allreduce_segments'] != 4 or layer['post_tp_scale_instructions'] != 2:
        raise ValueError('post-TP full-row scale schedule changed')
    for die, profile in enumerate(heads):
        decoded = [QI.decode_instruction(int(word, 16)) for word in profile['program_hex']]
        me = [item for item in decoded if item['unit'] == I.UNIT_ME and not item['me_wsrc']]
        pin = PINNED.get((GROUPS, TP))
        if (pin and len(me) != pin[3]) or me[0]['me_row0'] != 0:
            raise ValueError('head chunk or 18-bit row offset changed')
        if any(item['me_wbase'] != chunk['code_base'] or item['me_wcs'] != chunk['scale_base']
               or item['me_row0'] != chunk['first_row']
               for item, chunk in zip(me, profile['chunks'])):
            raise ValueError('head code/scale/row chunk mismatch')
        descriptor = QI.decode_descriptor(int(profile['descriptor_hex'][0], 16))
        if descriptor['row0'] != die * HEAD_ROWS:
            raise ValueError('head descriptor 18-bit row offset changed')


def binding(snapshot, out):
    pinned_snapshot(snapshot)
    tensor_count = source_shapes(snapshot)
    rows = compact_rows()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lay = FP.LayerZero(None, 0, rows)
    lay.emb_word = 0
    with FP.program_geometry(FP.vm_map()[0]):
        embed_program = P.build_program(lay, layers=[], embed=True, head=False, scale_bases=True)
    embed_words, embed_desc = QI.encode_segments(embed_program)
    layer = FP.profile(0, matrix_rows=rows, post_scale_bases=POST_SCALE_BASES)
    head_geometry = matrix(0, 'lm_head', HEAD_ROWS, 4096)
    head_geometry['scale_base'] = 0
    heads = [FP.profile_lm_head(die, head_geometry, 0) for die in range(TP)]
    check_stage_isa(embed_words, embed_desc, layer, heads, rows)
    files = []
    files.append(write_hex(out, 'embed_program', embed_words, I.INSTR_BITS))
    files.append(write_hex(out, 'embed_segments', embed_desc, 64))
    files.append(write_hex(out, 'layer_program', (int(x, 16) for x in layer['program_hex']), I.INSTR_BITS))
    files.append(write_hex(out, 'layer_segments', (int(x, 16) for x in layer['descriptor_hex']), 64))
    for die, profile in enumerate(heads):
        files.append(write_hex(out, f'head_program_d{die}',
                               (int(x, 16) for x in profile['program_hex']), I.INSTR_BITS))
        files.append(write_hex(out, f'head_segments_d{die}',
                               (int(x, 16) for x in profile['descriptor_hex']), 64))
    files.append(write_final_norm(snapshot, out))
    pin = PINNED.get((GROUPS, TP))
    if len(embed_words) != 2 or (pin and (layer['program_words'] != 33 or heads[0]['program_words'] != pin[2])):
        raise ValueError('stage program word count changed')
    if QI.ROW_HIGH_OFFSET != 898 or QI.DESC_ROW_HIGH_OFFSET != 18:
        raise ValueError('18-bit row offset reserved bits changed')
    if I.A != 24 or I.N != 16 or I.INSTR_BITS != 1024:
        raise ValueError('legacy ISA widths changed; requalify fullshape overlay')
    stages = [{'kind': 'embedding', 'index': 0, 'program': 'embed_program.hex',
               'descriptors': 'embed_segments.hex', 'code_word_count': 151936 * 64,
               'scale_row_count': 151936, 'image_source': 'model.embed_tokens.weight'}]
    for n in range(36):
        stages.append({'kind': 'decoder_layer', 'index': n + 1, 'layer': n,
                       'program': 'layer_program.hex', 'descriptors': 'layer_segments.hex',
                       'image_directory': f'layers/L{n:02d}/d{{die}}',
                       'image_generator_argv': ['python3', 'tools/hdc_qwen_layer0_rom_w12.py',
                                                '--snapshot', '{snapshot}', '--layer', str(n),
                                                '--compact-banks', '--die', '{die}', '--out',
                                                f'layers/L{n:02d}/d{{die}}'],
                       'code_words_per_die': sum(r['words'] for r in rows),
                       'scale_words_per_die': sum(r['scale_span_words'] for r in rows),
                       'crom_words': LAYER_CROM_WORDS,
                       'post_tp_scale_bases': list(POST_SCALE_BASES),
                       'allreduce_half_segments': 4})
    stages.append({'kind': 'lm_head', 'index': 37,
                   'program_by_die': ['head_program_d0.hex', 'head_program_d1.hex'],
                   'descriptors_by_die': ['head_segments_d0.hex', 'head_segments_d1.hex'],
                   'image_source': 'lm_head.weight', 'final_norm_source': 'model.norm.weight',
                   'final_norm_crom': 'head_final_norm_crom.hex',
                   'rows_per_die': HEAD_ROWS,
                   'code_words_per_die': head_geometry['words'],
                   'scale_words_per_die': head_geometry['rounds'] * (GROUPS // head_geometry['split']) * I.INTERLEAVE,
                   'chunks_per_die': len(heads[0]['chunks'])})
    sources = ('tools/qwen_o4_fulltoken_binding_w12.py', 'tools/hdc_qwen_fullshape_isa_w12.py',
               'tools/hdc_qwen_fullshape_program_w12.py', 'tools/hdc_qwen_layer0_rom_w12.py',
               'tools/hdc_qwen_int8_image_w12.py', 'tools/hdc_qwen_vocab_rom.py',
               'tools/hdc_program.py', 'tools/hdc_isa.py')
    manifest = {'schema': 'opentallas.qwen-o4-fulltoken-binding.v1',
                'status': 'source_and_program_preflight', 'tp': TP, 'groups': GROUPS, 'layers': 36,
                'stage_count': len(stages), 'checkpoint_revision': snapshot.name,
                'checkpoint_lock_sha256': sha(LOCK), 'config_sha256': sha(CONFIG),
                'checkpoint_index_sha256': sha(snapshot / 'model.safetensors.index.json'),
                'source_tensor_shapes_checked': tensor_count,
                'source_sha256': {name: sha(ROOT / name) for name in sources},
                'program_sha256': {path.name: sha(path) for path in files},
                'requirements': {'core_token_bits': 18, 'core_address_bits': 24,
                                 'me_row0_high_bits': [899, 898],
                                 'tp_descriptor_row0_high_bits': [19, 18],
                                 'independent_scale_base': 'INT8_SCALE_WCS_BASE=1',
                                 'embedding_code_address': 'token*64 + in_row_word',
                                 'embedding_rows': 'replicated 4096 INT8 codes and one BF16 scale per token per die',
                                 'head_argmax': '18-bit vocabulary row index from 75968-row die halves',
                                 'code_and_scale_banks': 'stage-local compact, rebased per invocation',
                                 'kv': 'page one 8192-token layer window before each layer',
                                 'control': 'invoke stages in order, preserve VM X and select image bank'},
                'vm_elems': FP.vm_map()[1], 'kv_window_elems': 2 * 4 * 8192 * 128,
                'compact_layer_matrix_layout': rows, 'stages': stages,
                'claim_boundary': 'All-stage source/ISA/image address binding only; full payloads, RTL layer execution and token exactness unproved.'}
    (out / 'fulltoken_binding.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = binding(args.snapshot, args.out)
    print(json.dumps({'status': result['status'], 'stages': result['stage_count'],
                      'source_tensors': result['source_tensor_shapes_checked']}))


if __name__ == '__main__':
    main()
