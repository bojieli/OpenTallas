"""Released-table physical partition shared by HBM compiler and allocation book.

This is an address/metadata contract, not native full-token qualification.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

LAYERS = (1, 14)
RELEASED_ROWS = (384_006_168, 384_016_682)
HOMES = (tuple(range(8)), tuple(range(8, 16)))
ROW_BYTES = 288
TABLE_BASE = 96 << 30
STACK_BYTES = 22_500_000_000
DATA_WIN = 20 << 30
SLOTS = 24
COUNT_BASE = 32
ROWS_BASE = 40
TABLE_WORDS = ROWS_BASE + 8 * SLOTS  # 232 U32, 29 sectors; legacy four-home table was 144.


def rows_per_home(nrows):
    if not 0 < nrows < (1 << 29):
        raise ValueError('Engram rows must fit released 29-bit row protocol')
    return (int(nrows) + 7) // 8


def locate(row, nrows, layer_index):
    if layer_index not in (0, 1) or not 0 <= int(row) < nrows:
        raise ValueError('Engram layer/row outside physical table')
    rph = rows_per_home(nrows)
    home, local = divmod(int(row), rph)
    return home, HOMES[layer_index][home], local


def host_table(ids, nrows, layer_index):
    ids = [int(x) for x in ids]
    if len(ids) != SLOTS:
        raise ValueError('Engram token must contain exactly 24 row IDs')
    out = [0] * TABLE_WORDS
    counts = [0] * 8
    for j, row in enumerate(ids):
        h, rank, local = locate(row, nrows, layer_index)
        slot = counts[h]
        out[j] = (slot // 8) * 768 + 8 * rank + slot % 8
        out[ROWS_BASE + SLOTS * h + slot] = local
        counts[h] += 1
    out[COUNT_BASE:COUNT_BASE + 8] = counts
    return out


def allocation_manifest():
    intervals = []
    for li, nrows in enumerate(RELEASED_ROWS):
        rph = rows_per_home(nrows)
        for h, rank in enumerate(HOMES[li]):
            first = h * rph
            rows = min(rph, nrows - first)
            size = rows * ROW_BYTES
            assert size <= DATA_WIN < STACK_BYTES
            intervals.append(dict(layer=LAYERS[li], layer_index=li, home=h, rank=rank,
                stack=3, stack_local_begin=0, stack_local_end=size,
                logical_address_begin=TABLE_BASE, logical_address_end=TABLE_BASE + size,
                global_row_begin=first, global_row_end=first + rows, rows=rows,
                row_bytes=ROW_BYTES, padding_rows=0))
        assert sum(x['rows'] for x in intervals if x['layer_index'] == li) == nrows
    return dict(schema='opentallas.hbm.engram.partition.v1', homes_per_layer=8,
        row_bytes=ROW_BYTES, table_words=TABLE_WORDS, intervals=intervals,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        status='candidate_source_contract', native_qualified=False,
        scope='Released row coverage and stack extents only; actual DMA/COLL/calendar/physical join required')


if __name__ == '__main__':
    print(json.dumps(allocation_manifest(), indent=2))
