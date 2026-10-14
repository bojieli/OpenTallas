#!/usr/bin/env python3
"""Source-bound TP8 token plan; no RTL execution or token timing claim."""
import argparse
import hashlib
import json
from pathlib import Path

import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as ISA
import hdc_qwen_fullshape_program_w12 as FP
from hdc_qwen_fullshape_placement_w12 import TP, GROUPS, LOCK, CONFIG, matrix
from hdc_qwen_layer0_rom_w12 import pinned_snapshot
from qwen_o4_fulltoken_binding_w12 import compact_rows, source_shapes, write_final_norm, write_hex
from qwen_tp8_fused_attention_lower import lower_validated

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_heads(heads):
    if len(heads) != 8:
        raise ValueError('eight distinct head rank descriptors required')
    for rank, head in enumerate(heads):
        fields = [ISA.decode_instruction(int(w, 16)) for w in head['program_hex']]
        chunks = [f for f in fields if f['unit'] == I.UNIT_ME]
        if len(chunks) != len(head['chunks']) or sum(f['me_nout'] for f in chunks) != 18992:
            raise ValueError('complete head shard coverage required')
        next_row = 0
        for f, chunk in zip(chunks, head['chunks']):
            if f['me_row0'] != next_row or f['me_row0'] != chunk['first_row']:
                raise ValueError('head chunk row offset changed')
            if not f['me_amax'] or f['me_oen'] or f['me_wsrc']:
                raise ValueError('head must execute real ROM argmax')
            if f['me_wbase'] != chunk['code_base'] or f['me_wcs'] != chunk['scale_base']:
                raise ValueError('head code/scale bank mismatch')
            next_row += f['me_nout']
        desc = ISA.decode_descriptor(int(head['descriptor_hex'][0], 16))
        if desc['kind'] != P.COLL_ARGMAX or desc['row0'] != rank * 18992:
            raise ValueError('head global 18-bit rank offset changed')


def plan(snapshot, out):
    if (TP, GROUPS, I.W_LANES, I.INTERLEAVE) != (8, 3072, 16, 8):
        raise ValueError('requires explicit TP8/GT3072/W16/IL8 environment')
    pinned_snapshot(snapshot)
    tensors = source_shapes(snapshot)
    out.mkdir(parents=True, exist_ok=True)
    rows = compact_rows()
    rope = 2 * 4096 + (4 + 1) * 128 + 1
    post_bases = (rope + 8192 * 64, rope + 8192 * 64 + 4096)
    layer = FP.profile(0, matrix_rows=rows, post_scale_bases=post_bases)
    if layer['program_words'] != 29 or layer['allreduce_segments'] != 2:
        raise ValueError('native source profile must retain two full-row collectives')
    fields = [ISA.decode_instruction(int(w, 16)) for w in layer['program_hex']]
    original_bytes = ''.join(w + '\n' for w in layer['program_hex']).encode()
    fused = lower_validated(layer, {'program_sha256': hashlib.sha256(original_bytes).hexdigest(),
                                   'instructions': [{'encoded_fields': f} for f in fields]})
    if fused['program_words'] != 25 or post_bases != (533121, 537217):
        raise ValueError('native lowering/post-scale geometry changed')
    files = [write_hex(out, 'layer_source_program', (int(w, 16) for w in layer['program_hex']), 1024),
             write_hex(out, 'layer_candidate_program', (int(w, 16) for w in fused['program_hex']), 1024),
             write_hex(out, 'layer_candidate_segments', (int(w, 16) for w in fused['descriptor_hex']), 64)]
    lay = FP.LayerZero(None, 0, rows)
    lay.emb_word = 0
    with FP.program_geometry(FP.vm_map()[0]):
        embed = P.build_program(lay, layers=[], embed=True, head=False, scale_bases=True)
    embed_words, embed_desc = ISA.encode_segments(embed)
    if len(embed_words) != 2 or ISA.decode_instruction(embed_words[0])['a_d'] != I.DYN_EMBED:
        raise ValueError('actual token-addressed embedding instruction required')
    files += [write_hex(out, 'embedding_program', embed_words, 1024),
              write_hex(out, 'embedding_segments', embed_desc, 64), write_final_norm(snapshot, out)]
    head_geometry = matrix(0, 'lm_head', 18992, 4096)
    head_geometry['scale_base'] = 0
    heads = [FP.profile_lm_head(rank, head_geometry, 0) for rank in range(8)]
    validate_heads(heads)
    for rank, head in enumerate(heads):
        files += [write_hex(out, f'head_program_rank{rank}', (int(w, 16) for w in head['program_hex']), 1024),
                  write_hex(out, f'head_segments_rank{rank}', (int(w, 16) for w in head['descriptor_hex']), 64)]
    sources = [Path(__file__), Path(FP.__file__), Path(P.__file__), Path(I.__file__), Path(ISA.__file__),
               ROOT / 'tools/qwen_o4_fulltoken_binding_w12.py', ROOT / 'tools/qwen_tp8_fused_attention_lower.py',
               ROOT / 'tools/hdc_qwen_fullshape_placement_w12.py', ROOT / 'tools/hdc_qwen_layer0_rom_w12.py']
    report = {'schema': 'opentallas.qwen-tp8-token-source-plan.v1', 'status': 'source_preflight_only',
              'checkpoint_revision': snapshot.name, 'checkpoint_lock_sha256': sha(LOCK),
              'config_sha256': sha(CONFIG), 'checkpoint_index_sha256': sha(snapshot / 'model.safetensors.index.json'),
              'source_tensor_shapes_checked': tensors, 'tp': 8, 'groups': 3072, 'layers': 36,
              'stage_count': 38, 'layer_original_words': 29, 'layer_candidate_words': 25,
              'layer_collectives': 2, 'layer_crom_words': post_bases[1] + 4096,
              'post_tp_scale_bases': list(post_bases), 'layer_matrix_layout': rows,
              'head_geometry': head_geometry, 'head_profiles': heads,
              'files_sha256': {p.name: sha(p) for p in files},
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources},
              'required_core': {'NW': 18, 'INT8_EMBED': 1, 'INT8_SCALE_WCS_BASE': 1,
                                'VM_elements': FP.vm_map()[1], 'KV_elements_per_rank_layer': 2 * 8192 * 128},
              'embedding': {'rows': 151936, 'codes_per_row': 4096, 'code_words_per_row': 64,
                            'source': 'model.embed_tokens.weight', 'scale': 'one BF16 W8 scale per global token'},
              'layer_images': [{'layer': n, 'ranks': list(range(8)), 'payload_status': 'not_bound_by_this_plan'}
                               for n in range(36)],
              'remaining_contracts': ['Actual NW18/INT8_EMBED execution; existing fullcore NW16 layer-only build is insufficient',
                                     'All36 immutable real payloads and real prior-KV provenance',
                                     'No-reset executed previous-layer VM/X carry and actual accepted IB/context/version',
                                     'Production cached-ROM/X-band, constant/VM/TT clock and station composition',
                                     'Eight real head argmax partials and production global argmax collector',
                                     'HOST true token completion and unified measured token timing'],
              'claim_boundary': 'Checkpoint metadata, actual final-norm constants and source-derived programs only. No all36 payload, execution, token or cost proof.'}
    (out / 'token_source_plan.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    report = plan(args.snapshot, args.out)
    print(json.dumps({k: report[k] for k in ('status', 'stage_count', 'source_tensor_shapes_checked', 'layer_crom_words')}))
