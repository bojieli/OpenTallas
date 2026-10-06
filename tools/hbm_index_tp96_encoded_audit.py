#!/usr/bin/env python3
"""Cross-check historical TP4 encoded sectors against the retained L20 store.

This reads source operands only; it computes no scores and supplies no DUT oracle.
The separately appended current row is absent from these historical images.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from hbm_index_tp96_producer import STORE_SHA, sha

PINS = (
    'a8c2255fae6bb45ff177e216ccc4ba26b336668fb0a993f7b1a3f1d6b2271d4d',
    '6e72abe9e46351e86a371d92a81f5bc47a147745f6ee48168cbf761514b39cae',
    '557bca6fd6e96af46298faf8af88da8e338dcef8393b81ca09c5e9b6b68ab0de',
    'bd07cb0be7d6157d6570d327c9edfa3e8fb0c346f8bb90e504cdfc55053bcb2f',
)


def audit(images, store):
    if sha(store) != STORE_SHA:
        raise ValueError('retained decoded store pin differs')
    keys = np.load(store, mmap_mode='r')
    if keys.shape != (1048575, 128) or keys.dtype != np.float32:
        raise ValueError('actual entering key shape/type differs')
    magnitudes = np.array([0, .5, 1, 1.5, 2, 3, 4, 6], np.float32)
    table = np.concatenate((magnitudes, -magnitudes))
    records = []
    for rank, pin in enumerate(PINS):
        path = images / f'r{rank}' / 'ikhbm_region.hex'
        if sha(path) != pin:
            raise ValueError(f'encoded shard {rank} pin differs')
        lo, hi = rank * 262144, min((rank + 1) * 262144, len(keys))
        sectors = np.zeros((256 * 17 * 128, 32), np.uint8)
        present = np.zeros(len(sectors), bool)
        count = 0
        with path.open() as f:
            for line in f:
                address, data = line.split()
                address = int(address, 16)
                if address >= len(sectors) or present[address] or len(data) != 64:
                    raise ValueError('invalid or duplicated custom sector record')
                sectors[address] = np.frombuffer(bytes.fromhex(data)[::-1], np.uint8)
                present[address] = True
                count += 1
        expected_count = 557056 if rank < 3 else 557054
        if count != expected_count:
            raise ValueError('historical shard sector extent differs')
        decoded_hash = hashlib.sha256()
        for start in range(0, hi - lo, 1024):
            t = np.arange(start, min(start + 1024, hi - lo))
            b, tt = t // 1024, t % 1024
            code_addr = (17 * b + 1 + tt // 64) * 128 + 2 * (tt % 64)
            scale_addr = 17 * b * 128 + tt // 8
            if not np.all(present[code_addr] & present[code_addr + 1] & present[scale_addr]):
                raise ValueError('required key sector missing')
            packed = np.concatenate((sectors[code_addr], sectors[code_addr + 1]), axis=1)
            codes = np.empty((len(t), 128), np.uint8)
            codes[:, 0::2], codes[:, 1::2] = packed & 15, packed >> 4
            scales = sectors[scale_addr[:, None], (tt % 8)[:, None] * 4 + np.arange(4)]
            if np.any(scales >= 253):
                raise ValueError('reserved UE8M0 source scale')
            decoded = np.ldexp(table[codes], np.repeat(scales.astype(np.int16) - 127, 32, axis=1))
            actual = keys[lo + start:lo + start + len(t)]
            if not np.array_equal(decoded.view(np.uint32), actual.view(np.uint32)):
                bad = np.argwhere(decoded.view(np.uint32) != actual.view(np.uint32))[0]
                raise ValueError(f'encoded/decoded source bits differ gid={lo+start+int(bad[0])} dim={bad[1]}')
            decoded_hash.update(decoded.tobytes())
        records.append(dict(path=str(path), sha256=pin, global_range=[lo, hi],
                            sectors=count, decoded_float32_sha256=decoded_hash.hexdigest()))
    return dict(status='PASS_ALL_HISTORICAL_ENCODED_KEY_BITS_MATCH_RETAINED_STORE',
                keys=len(keys), values=int(keys.size), store_sha256=STORE_SHA,
                shards=records, current_row_excluded=True, score_computation=False,
                DUT_execution=False, TP96_replication=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--images', type=Path, required=True)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.images, a.store)
    result['audit_source_sha256'] = sha(__file__)
    with a.out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(result['status'])
