#!/usr/bin/env python3
"""Finite source-only spill write plan; no COPY, scratch or calendar adoption."""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path


def plan(repo, image, manifest):
    sys.path.insert(0, str(repo / 'tools/hbm_next'))
    from isa_loader import load_isa
    IR, IC = load_isa()
    raw = image.read_bytes()
    records = IC.decode_all(raw)
    meta = json.loads(manifest.read_text())['records']
    assert len(records) == len(meta)
    fragments = []
    stores = 0
    for command, ((offset, rec, rx, encoded), origin) in enumerate(zip(records, meta)):
        assert origin['offset'] == offset and origin['bytes'] == len(encoded)
        if (rec.unit, rec.op) != ('DMA', 'STORE'):
            continue
        for bank, scalar in IR.expand(rec, rx):
            a, o = scalar.desc['A'], scalar.desc['O']
            assert a.space == 'VM' and o.space == 'HBM'
            assert a.fmt == o.fmt == 'U32' and a.m == o.m == 1 and a.n == o.n
            assert not any([a.indexed, o.indexed, a.dyn_mul, o.dyn_mul,
                            a.lstride, o.lstride, a.l1stride, o.l1stride, a.n_sel, o.n_sel])
            assert a.istride in (0, 1) and o.istride in (0, 1)
            assert 0 <= a.base < a.base + a.n <= 262144
            assert o.base >> 35 == 3 and o.base % 32 == 0 and a.base % 8 == 0 and a.n % 8 == 0
            stores += 1
            consumed = 0
            while consumed < a.n:
                src = a.base + consumed
                byte = o.base + consumed * 4
                sector = (byte & ((1 << 35) - 1)) // 32
                quad = ((sector >> 6) ^ (sector >> 11) ^ (sector >> 16)) & 1
                ordinal = ((sector >> 7) << 6) | (sector & 63)
                folded = ((ordinal >> 6) << 7) | (((quad ^ (ordinal >> 10) ^ (ordinal >> 15)) & 1) << 6) | (ordinal & 63)
                assert folded == sector
                # A real-sector64 boundary can change the PHY half. Cap512
                # words for the explicitly proposed two512-word scratch slots.
                n = min(a.n - consumed, (64 - (sector & 63)) * 8,
                        512, 65536 - (src & 65535))
                assert n > 0 and n % 8 == 0
                end = sector + n // 8 - 1
                assert end < 703125000
                assert (((end >> 6) ^ (end >> 11) ^ (end >> 16)) & 1) == quad
                assert (((end >> 7) << 6) | (end & 63)) == ordinal + n // 8 - 1
                # The real DBK request embeds stk_q as its VM SID. An
                # aligned address in another SID is still unreachable by this
                # writer; it needs a real bank-changing producer as well.
                staged = src % 64 != 0 or src // 65536 != 3
                native_source = 64512 if staged else (src & 65535)
                native_SID = 3
                assert native_source % 64 == 0 and native_source + n <= 65536
                native_destination = (3 << 35) | (ordinal << 5)
                move227 = (1 | (5 << 2) | (native_source << 5) | (1 << 77) |
                           (5 << 95) | (native_destination << 98) |
                           (1 << 170) | (1 << 186) | (n << 206))
                assert move227.bit_length() <= 227
                fragments.append(dict(resident_command=command, DYN_bank=bank,
                    source_word=src, source_SID=src // 65536, words=n,
                    stack=3, target_byte=byte, real_sector=sector, quad=quad,
                    quadrant_ordinal=ordinal, requires_staging=staged,
                    staging_reasons=(["alignment"] if src % 64 else []) +
                        (["writer_source_SID"] if src // 65536 != 3 else []),
                    proposed_scratch_word=261120 if staged else None,
                    candidate_native_source_local_word=native_source,
                    candidate_native_source_SID=native_SID,
                    candidate_move227_hex=f'{move227:057x}',
                    selected_local_SU_source_SID_present=src // 65536 in (2, 3)))
                consumed += n
    staged = [x for x in fragments if x['requires_staging']]
    count_q = collections.Counter(x['quad'] for x in fragments)
    summary = dict(status='SOURCE_ONLY_FINITE_PLAN_NO_COPY_OR_SCRATCH_ADOPTION',
        image_sha256=hashlib.sha256(raw).hexdigest(), STORE_records=stores,
        scalar_words=sum(x['words'] for x in fragments), native_fragments=len(fragments),
        fragment_words_max=max(x['words'] for x in fragments),
        fragments_by_quad=dict(count_q),
        CP128_pages_per_quad_lower_bound={q: (n + 127) // 128 for q, n in count_q.items()},
        CP_table_configuration_words_256b=2 * len(fragments),
        CP_table_payload_bytes=64 * len(fragments),
        native_issue_groups_64words=sum((x['words'] + 63) // 64 for x in fragments),
        native_drain_groups_64words=sum((x['words'] + 63) // 64 for x in fragments),
        physical_write_columns_32bytes=sum(x['words'] // 8 for x in fragments),
        maximum_real_window_span_sectors=max(x['words'] // 8 for x in fragments),
        staged_fragments=len(staged), staged_words=sum(x['words'] for x in staged),
        staged_bytes=4 * sum(x['words'] for x in staged),
        stage_read_sectors_lower_bound=sum(x['words'] // 8 for x in staged),
        stage_write_sectors_lower_bound=sum(x['words'] // 8 for x in staged),
        original_source_SID_fragments=dict(collections.Counter(x['source_SID'] for x in fragments)),
        SID0_1_original_source_fragments=sum(x['source_SID'] < 2 for x in fragments),
        staged_fragments_missing_local_SU_source=sum(x['source_SID'] < 2 for x in staged),
        holds=['Current selected writer pair is STK2; no STK3 writer installed.',
            'The proposed [261120,262144) scratch lease is NOT reserved. A slot is owned before staging until true WB ACK/fence; serialize if reusing slot0.',
            'No selected VM0/1 bank-changing staging path identified. Generic COPY and pure local BYPASS are not substitutes.',
            'No live scratch data, extra VM ports, cross-quarter source route or host configuration bandwidth assumed.',
            'Candidate227 is literal U32/VM-local to STK3 quadrant-ordinal fields, UNEXECUTED. Native source SID is fixed to the writer STK3 strap. Every SID0/1/2 source therefore needs real staging into SID3, even when already 64-word aligned; no external binding or address alias supplies it.',
            'CP page counts are capacity lower bounds for this explicit512word/boundary fragmentation only; original-order barriers/page handoff can add work. They are not an optimal fragment-count claim.',
            'SID2/3 local SU presence does not prove bank-changing COPY, cross-half write ownership or a STK3 writer route.',
            'No source staging overlap, global calendar, TPS or physical credit.'],
        COPY_edges=None, issue_dates=None, drain_dates=None, HOST_wire_edges=None,
        representative_fragments=fragments[:8])
    return summary, fragments


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'image', 'manifest', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    summary, fragments = plan(a.repo, a.image, a.manifest)
    (a.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (a.out / 'fragments.json').write_text(json.dumps(fragments, separators=(',', ':')) + '\n')
    print(json.dumps(summary))
