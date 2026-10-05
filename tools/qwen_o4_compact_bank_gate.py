#!/usr/bin/env python3
"""Prove compact Qwen layer-0 code/scale ROM banks preserve emitted arithmetic."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import hdc_isa as I

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'results/rtl/qwen_o4_layer0_compact_banks.json'
CODE_WIDTH = 6144 * 16 * 2 + 1
SCALE_WIDTH = 16 * 4 + 1


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image(folder: Path) -> dict:
    manifest = json.loads((folder / 'layer0_rom.json').read_text())
    if manifest['status'] != 'image_and_isa_emitted' or manifest['layer'] != 0:
        raise ValueError('expected real layer-0 image')
    for name, digest in manifest['source_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f'stale emitter source: {name}')
    for name, digest in manifest['image_sha256'].items():
        if sha(folder / name) != digest:
            raise ValueError(f'stale image: {folder}/{name}')
    return manifest


def span_hash(path: Path, base: int, words: int, width: int) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        stream.seek(base * width)
        for _ in range(words):
            line = stream.read(width)
            if len(line) != width or line[-1:] != b'\n':
                raise ValueError(f'short or malformed word in {path}')
            digest.update(line)
    return digest.hexdigest()


def compare_images(padded: Path, compact: Path) -> dict:
    pm, cm = image(padded), image(compact)
    if pm['rom_bank_layout'] != 'shared_base_padded' or cm['rom_bank_layout'] != 'independent_compact':
        raise ValueError('ROM layout modes differ from expected pair')
    if pm['die'] != cm['die'] or pm['checkpoint_revision'] != cm['checkpoint_revision']:
        raise ValueError('checkpoint or TP die differs')
    matrices = []
    for p, c in zip(pm['matrix_layout'], cm['matrix_layout'], strict=True):
        for key in ('name', 'rows', 'columns', 'split', 'rounds', 'code_span_words', 'scale_span_words'):
            if p[key] != c[key]:
                raise ValueError(f'{p["name"]}: geometry changed: {key}')
        code_p = span_hash(padded / 'matrix_int8.hex', p['base'], p['code_span_words'], CODE_WIDTH)
        code_c = span_hash(compact / 'matrix_int8.hex', c['base'], c['code_span_words'], CODE_WIDTH)
        scale_p = span_hash(padded / 'matrix_scale_bf16.hex', p['scale_base'], p['scale_span_words'], SCALE_WIDTH)
        scale_c = span_hash(compact / 'matrix_scale_bf16.hex', c['scale_base'], c['scale_span_words'], SCALE_WIDTH)
        if code_p != code_c or scale_p != scale_c:
            raise ValueError(f'{p["name"]}: requested code or scale word changed')
        matrices.append({'name': p['name'], 'code_words_exact': p['code_span_words'],
                         'scale_words_exact': p['scale_span_words'],
                         'code_stream_sha256': code_p, 'scale_stream_sha256': scale_p,
                         'padded_code_base': p['base'], 'compact_code_base': c['base'],
                         'padded_scale_base': p['scale_base'], 'compact_scale_base': c['scale_base']})
    pwords = [I.decode(int(x, 16)) for x in (padded / 'program.hex').read_text().splitlines()]
    cwords = [I.decode(int(x, 16)) for x in (compact / 'program.hex').read_text().splitlines()]
    if len(pwords) != len(cwords) or sha(padded / 'segments.hex') != sha(compact / 'segments.hex'):
        raise ValueError('instruction count or TP segments changed')
    relocated = []
    for pc, (p, c) in enumerate(zip(pwords, cwords, strict=True)):
        changed = {key for key in p if p[key] != c[key]}
        if changed and (p['unit'] != I.UNIT_ME or p['me_wsrc'] or changed - {'me_wbase', 'me_wcs'}):
            raise ValueError(f'PC{pc}: non-address instruction field changed: {changed}')
        if changed:
            relocated.append(pc)
    return {'die': pm['die'], 'matrices': matrices, 'relocated_weight_pcs': relocated,
            'program_words': len(pwords), 'segments_sha256': sha(padded / 'segments.hex'),
            'padded_code_bytes': pm['matrix_words'] * ((CODE_WIDTH - 1) // 2),
            'compact_code_bytes': cm['matrix_words'] * ((CODE_WIDTH - 1) // 2),
            'padded_scale_bytes': pm['scale_rom_words'] * ((SCALE_WIDTH - 1) // 2),
            'compact_scale_bytes': cm['scale_rom_words'] * ((SCALE_WIDTH - 1) // 2),
            'padded_manifest_sha256': sha(padded / 'layer0_rom.json'),
            'compact_manifest_sha256': sha(compact / 'layer0_rom.json')}


def oracle(path: Path) -> dict:
    data = json.loads((path / 'oracle.json').read_text())
    if data['status'] != 'ISA_golden_only':
        raise ValueError('oracle status is not a golden reference')
    for name, digest in data['oracle_source_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f'stale oracle source: {name}')
    for die, vectors in data['outputs'].items():
        for name, entry in vectors.items():
            if sha(path / f'{die}_{name}.hex') != entry['sha256']:
                raise ValueError(f'stale oracle vector: {die}_{name}')
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--padded-prefix', type=Path, default=Path('/tmp/qwen-real-layer0-padded'))
    ap.add_argument('--compact-prefix', type=Path, default=Path('/tmp/qwen-real-layer0-compact'))
    ap.add_argument('--padded-oracle', type=Path, default=Path('/tmp/qwen-layer0-oracle-padded'))
    ap.add_argument('--compact-oracle', type=Path, default=Path('/tmp/qwen-layer0-oracle-compact'))
    ap.add_argument('--output', type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    dies = [compare_images(Path(f'{args.padded_prefix}-d{die}'), Path(f'{args.compact_prefix}-d{die}'))
            for die in range(2)]
    po, co = oracle(args.padded_oracle), oracle(args.compact_oracle)
    if po['x_preload_sha256'] != co['x_preload_sha256']:
        raise ValueError('oracle input activation changed')
    vector_hashes = {}
    for die in ('die0', 'die1'):
        vector_hashes[die] = {}
        for name, entry in po['outputs'][die].items():
            digest = entry['sha256']
            if co['outputs'][die][name]['sha256'] != digest:
                raise ValueError(f'{die}_{name}: compact ISA result differs')
            vector_hashes[die][name] = digest
    result = {'schema': 'opentallas.qwen-o4-layer0-compact-rom.v1', 'status': 'exact_image_and_ISA_equivalence',
              'source_sha256': {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
                                'tools/hdc_qwen_layer0_rom.py': sha(ROOT / 'tools/hdc_qwen_layer0_rom.py'),
                                'tools/qwen_o4_layer0_oracle.py': sha(ROOT / 'tools/qwen_o4_layer0_oracle.py')},
              'dies': dies, 'oracle_sha256': {'padded': sha(args.padded_oracle / 'oracle.json'),
                                             'compact': sha(args.compact_oracle / 'oracle.json')},
              'exact_oracle_vector_sha256': vector_hashes,
              'per_die_savings_bytes': {'code_ROM': dies[0]['padded_code_bytes'] - dies[0]['compact_code_bytes'],
                                        'scale_ROM': dies[0]['padded_scale_bytes'] - dies[0]['compact_scale_bytes']},
              'claim_boundary': 'All requested code/scale words and both ISA-oracle layer0 traces match bit for bit. '
                                'This is an opt-in image/ISA capacity gate; no compact-bank RTL, ROM macro packing, '
                                'route, full token, or rate is measured.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'per_die_savings_bytes': result['per_die_savings_bytes'],
                      'oracle_vectors_checked': sum(map(len, vector_hashes.values()))}, indent=2))


if __name__ == '__main__':
    main()
