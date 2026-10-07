#!/usr/bin/env python3
"""One source-bench fixture; expected data is comparison-only, never a DUT input.

This does not compile another native engine archive or replay a passing gate.
The bench requires the actual native RTL, or a source-matched standalone
quarter executable supplied by its archive owner. Interface-only elaboration
is explicitly not native runtime evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rtl_w11_idx_array as W
import rtl_hdc_v41x_idx_campaign as C
import hdc_golden_v41 as G

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    token = W.normal_token(np.random.default_rng(1062026), 64, keep_p=1)
    blocks = [0, 1, 513, 514, 1024, 1025, 1364, 1365]
    ids = [8 * (96 * blocks[k // 8]) + k % 8 for k in range(64)]
    assert len(set(ids)) == 64 and max(ids) < (1 << 20)
    queries = [C.hexline([(int(c), 4) for c in token['qc'][h]] +
                        [(int(u), 8) for u in token['qu'][h]] +
                        [(int(G.bits(token['w'][h])) >> 16, 16)]) for h in range(32)]
    keys, expected = [], []
    for k in range(64):
        # One real reader refusal and three invalid/undriven slots. No causal
        # pre-mask: every valid non-refused native score uses the golden order.
        refused, valid = k == 19, k < 61
        word = int(C.hexline([(int(c), 4) for c in token['kc'][k]] +
                            [(int(u), 8) for u in token['ku'][k]]), 16)
        keys.append(C.hexline([(word, 544), (int(refused), 1),
                               (ids[k], 20), (int(valid), 1)]))
        score = 0 if refused else int(token['exp'][k])
        fault = refused or bool(token['fault'][k])
        expected.append(C.hexline([(score, 16), (int(fault), 1)]))
    for filename, lines in [('query.mem', queries), ('keys.mem', keys),
                            ('expected.mem', expected)]:
        (args.out / filename).write_text('\n'.join(lines) + '\n')
    pins = ['rtl/dsrom_sys/reindex_parent/ot_dsrom_reindex_native_quarter.sv',
            'rtl/dsrom_sys/reindex_parent/tb_dsrom_reindex_native_quarter.sv',
            'rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv',
            'tools/dsrom_reindex_native_quarter_fixture.py',
            'tools/rtl_w11_idx_array.py', 'tools/rtl_hdc_v41x_idx_campaign.py',
            'tools/hdc_golden_v41.py']
    record = dict(scope='One prepared 16-lane native quarter source bench, not an executed runtime gate',
                  shape=dict(NS=4, NK=4, NB=4, IH=32, IW=20, MD=64, FPL=7, FML=5, QL=5),
                  seed=1062026, beats=4, valid_score_comparisons=61,
                  refused=1, invalid_undriven=3, global_IDs=ids,
                  source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in pins},
                  fixture_sha256={p: hashlib.sha256((args.out / p).read_bytes()).hexdigest()
                                  for p in ['query.mem', 'keys.mem', 'expected.mem']},
                  runtime_executed=False, native_runtime_pass=False, parent_qualified=False,
                  checks=['golden BF16 and fault', 'literal full global IDs',
                          'source bubbles', 'sink backpressure and held output',
                          'cold reset with accepted native work followed by query reload',
                          'query overwrite admission blocked with retained scores', 'default OFF'])
    (args.out / 'fixture.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k: record[k] for k in ['beats', 'valid_score_comparisons', 'runtime_executed']}))


if __name__ == '__main__':
    main()
