#!/usr/bin/env python3
"""Enroll actual TP96 publications in the existing parent harness, no build/run.

The installed book supplies placements. Source data come exclusively from the
Noether emitter. The saved all-million scores are comparison-only and never
appear in an offered source image or final-sink transaction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from hbm_opt_integrated_20261005_gather import compile_normal_gather

PHASE = 'L20.op14.index_scores.pre_candidate_mask.local_top512'
GOLD_SHA = '5aaed10c1c559edac22c7acae25c3d72c53abc79518471262977de06488b5d45'
FINAL_REFERENCE = ROOT / 'results/rtl/hbm_index_tp96_producer_20261006/final_reference_r1/ids.u32'
FINAL_REFERENCE_SHA = 'fa5fd356d42ffeb6aae1d8eea2fd43f65192b27ba7bbffe054461fce034df19d'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def prepare(installation_path, producer_path, gold_path, output, book_path=None, book_sha=None):
    import numpy as np
    if book_path is None:
        installation = load(installation_path)
        root = installation_path.parent
        compiled = compile_normal_gather(installation, root)
        book = load(root / installation['workspace_path'])
        artifacts = installation['source_artifacts']
    else:
        # The external native-stage fixture uses the owner's allocator recipe,
        # not an invented normal-SM entry. It does not enroll a CMD bank or
        # qualify the production linked program; real runtime receipts remain
        # mandatory in either mode.
        if not book_sha or sha(book_path) != book_sha:
            raise ValueError('explicit owner-pinned allocation book required')
        book = load(book_path)
        if (book['schema'] != 'opentallas.ds20.installed_workspace.v1'
                or book['source_phase_required'] != PHASE
                or not book['recipe_successor']['original_layout_preserved']):
            raise ValueError('actual retained allocator successor required')
        root = ROOT
        local = book['index_local_sources']
        work = {w['name']: w for w in book['workspaces']}
        arena, sink = work['HBM_INDEX_GATHER_ARENA'], work['HBM_INDEX_RESULT_SINK']
        words = [0, local['scores']['base'] | local['ids']['base'] << 32,
                 arena['base'] | arena['end'] << 32, sink['base'] | sink['end'] << 32,
                 book['memory_bytes'], 96 | 512 << 16 | 32 << 32, 0, 0]
        compiled = dict(entry_pc=0, loader_words=[dict(data=w) for w in words])
        # Producer and phase pins are independently verified below. They do not
        # become a production installer publication merely by existing on disk.
        artifacts = None
    producer = load(producer_path)
    if artifacts is not None:
        # The emitted producer must be the exact producer enrolled in the book,
        # with canonical installer-relative paths. An absolute emitter scratch
        # path must not bypass the installer's source_artifacts authority.
        installed_producer = book['index_producer']
        for name in ('source_path', 'source_phase_path'):
            key = producer[name]
            if not isinstance(key, str):
                raise ValueError('producer source path must be a string')
            path = Path(key)
            if (path.is_absolute()
                    or not path.parts or '..' in path.parts
                    or path.as_posix() != key):
                raise ValueError('producer source path must be installer-root normalized: ' + str(key))
            if installed_producer.get(name) != key:
                raise ValueError('emitted producer differs from installed book source: ' + key)
            try:
                (root / path).resolve().relative_to(root.resolve())
            except ValueError:
                raise ValueError('producer source resolves outside installer root: ' + key)
            if key not in artifacts or sha(root / path) != artifacts[key]:
                raise ValueError('actual emitted producer/phase not installed and pinned: ' + key)
    phase_path = Path(producer['source_phase_path'])
    if not phase_path.is_absolute():
        phase_path = root / phase_path
    phase = load(phase_path)
    if producer['source_path'] != 'tools/hbm_index_tp96_producer.py':
        raise ValueError('selected actual TP96 producer required')
    if any(producer.get(k) != v for k, v in {
        'rank_count': 96, 'candidates_per_rank': 512, 'score_dtype': 'FP32',
        'id_dtype': 'U32', 'rank_stride_bytes': 2048, 'plane_bytes': 196608,
        'scores_span_name': 'scores', 'ids_span_name': 'ids', 'source_phase': PHASE,
    }.items()):
        raise ValueError('actual full TP96 separate-plane producer required')
    ranks = phase['ranks']
    if (phase['source_phase'] != PHASE or phase['candidate_mask_applied']
            or sorted(r['rank'] for r in ranks) != list(range(96))
            or any(r['topk_exact'] != 512 or r['score_compares'] not in (10920, 10928)
                   for r in ranks)):
        raise ValueError('all 96 actual native publications at the selected phase required')
    for name, pin in producer['payload_pins'].items():
        if sha(producer_path.parent / name) != pin:
            raise ValueError('actual emitted payload changed: ' + name)
    planes = {}
    for name in ('scores', 'ids'):
        raw = (producer_path.parent / (name + '.u32')).read_bytes()
        if len(raw) != 196608:
            raise ValueError('full plane byte extent required')
        planes[name] = np.frombuffer(raw, dtype='<u4')
        text = (producer_path.parent / (name + '.mem')).read_text().split()
        if len(text) != 3072 or any(len(w) != 128 for w in text):
            raise ValueError('actual 3072x512 plane image required')
        decoded = b''.join(int(w, 16).to_bytes(64, 'little') for w in text)
        if decoded != raw:
            raise ValueError('plane wire byte/lane order differs')
    ids = planes['ids']
    if len(np.unique(ids)) != 49152 or np.any(ids >= 1048576):
        raise ValueError('distinct literal global IDs required')
    for rank in range(96):
        part = ids[rank * 512:(rank + 1) * 512]
        if np.any((part // 8) % 96 != rank) or np.any(part[1:] <= part[:-1]):
            raise ValueError('actual rank ownership/order differs')
    # The actual installer must carry these full planes; local 2KiB descriptor
    # spans do not authorize a 192KiB plane. No placement inferred from examples.
    spans = book['index_full_sources']
    occupied = book['occupied']
    capacity = book['memory_bytes']
    if not 0 < capacity < (1 << 32) or len(occupied) > 255:
        raise ValueError('selected preinstall capacity/census differs')
    desc = [w['data'] for w in compiled['loader_words']]
    if (len(desc) != 8 or desc[0] >= (1 << 32) or desc[4] != capacity
            or desc[5] != 96 | (512 << 16) | (32 << 32) or desc[6:] != [0, 0]):
        raise ValueError('actual installed descriptor phase/geometry differs')
    arena_base, arena_end = desc[2] & 0xffffffff, desc[2] >> 32
    sink_base, sink_end = desc[3] & 0xffffffff, desc[3] >> 32
    if arena_end - arena_base != 393216 or sink_end - sink_base != 2048:
        raise ValueError('actual installed N96/512 arena and sink extents required')
    local_score, local_id = desc[1] & 0xffffffff, desc[1] >> 32
    extents = [(arena_base, arena_end), (sink_base, sink_end),
               (local_score, local_score + 2048), (local_id, local_id + 2048)]
    records = []
    for kind, name in enumerate(('scores', 'ids'), 1):
        span = spans[name]
        base, end = span['base'], span['end']
        if (span['kind'] != 'source' or span['producer'] != producer['source_path']
                or base % 64 or end - base != 196608 or end > capacity):
            raise ValueError('actual installed full-plane span required: ' + name)
        extents.append((base, end))
        records.extend((kind, rank, base + rank * 2048, base + (rank + 1) * 2048)
                       for rank in range(96))
    for span in occupied:
        base, end = span['base'], span['end']
        if base % 64 or end % 64 or not 0 <= base < end <= capacity:
            raise ValueError('actual occupied span malformed')
        # Local spans already appear in the actual occupied book. Identical
        # declarations are one reservation; partially overlapping ones fail.
        if (base, end) not in extents:
            extents.append((base, end))
        records.append((0, 0, base, end))
    ordered = sorted(extents)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('source/arena/sink/local/occupied reservations overlap')
    if sha(gold_path) != GOLD_SHA:
        raise ValueError('retained independent all-million golden pin differs')
    with np.load(gold_path) as z:
        saved = z['L20.index_scores']
        scores = saved.astype('<f4')
        if (saved.shape != (1048576,) or not np.isfinite(saved).all()
                or not np.array_equal(saved, scores.astype(saved.dtype))):
            raise ValueError('saved unmasked FP32-exact reference required')
        if not np.array_equal(planes['scores'], scores.view('<u4')[ids]):
            raise ValueError('actual source score differs from independent saved reference')
    # Exact captured independent final selection, comparison only. Preserve
    # its actual order; do not regenerate a host selection from scores.
    if sha(FINAL_REFERENCE) != FINAL_REFERENCE_SHA:
        raise ValueError('captured L20 final U32 reference pin differs')
    final_ids = np.fromfile(FINAL_REFERENCE, dtype='<u4')
    if final_ids.shape != (512,) or len(np.unique(final_ids)) != 512 or (final_ids >= 1048576).any():
        raise ValueError('captured final selection extent differs')
    output.mkdir(parents=True, exist_ok=False)
    for name in ('scores.mem', 'ids.mem'):
        shutil.copyfile(producer_path.parent / name, output / name)
    (output / 'sink_gold.mem').write_text(''.join(
        ''.join(f'{int(v):08x}' for v in reversed(final_ids[j:j + 16])) + '\n'
        for j in range(0, 512, 16)))
    (output / 'descriptor.mem').write_text(''.join(f'{w:016x}\n' for w in desc))
    (output / 'records.mem').write_text(''.join(
        f'{kind:08x} {rank:08x} {base:08x} {end:08x}\n'
        for kind, rank, base, end in records))
    cfg = [spans['scores']['base'], spans['ids']['base'], capacity,
           len(occupied), compiled['entry_pc'], 20, 20, 0]
    (output / 'formatter.cfg').write_text(''.join(f'{v:08x}\n' for v in cfg))
    source_pins = {str(producer_path): sha(producer_path), str(phase_path): sha(phase_path),
                   str(gold_path): GOLD_SHA, str(FINAL_REFERENCE): FINAL_REFERENCE_SHA}
    if book_path is not None:
        source_pins[str(book_path)] = book_sha
    else:
        source_pins[str(installation_path)] = sha(installation_path)
    manifest = dict(source_phase=PHASE, ranks=96, source_words=6144,
        source_bytes=393216, installed_spans=spans, occupied=occupied,
        source_pins=source_pins,
        files={p.name: sha(p) for p in output.iterdir()},
        independent_gold_usage='sink_gold.mem comparison only; never offered to DUT',
        installed_producer_paths_checked=artifacts is not None,
        installed_producer_source_artifacts={producer[k]: artifacts[producer[k]]
            for k in ('source_path', 'source_phase_path')} if artifacts is not None else None,
        native_external_stage_recipe=book_path is not None,
        normal_SM_entry_enrolled=book_path is None,
        producer_source_sha256=sha((root if artifacts is not None else ROOT) / producer['source_path']),
        production_installation_complete=False,
        hardware_reservation_granted=False, numerical_runtime_qualified=False,
        full_token_qualified=False, physical_qualified=False)
    (output / 'formatter_fixture.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--installation', type=Path)
    mode.add_argument('--book', type=Path)
    p.add_argument('--book-sha256')
    for name in ('producer', 'gold', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    prepare(a.installation, a.producer, a.gold, a.out, a.book, a.book_sha256)
