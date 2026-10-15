#!/usr/bin/env python3
"""Compile the native direct-seam TP8 QK control calendar (component boundary).

The external service is an explicit boundary, not a synthetic on-chip model.
Physical service, relay and clock owners must supply its implemented latency.
The pinned RTL bench measures si start c0, local control start c3, face request
c7, external response c7+L, ring write c10+L, consume c37 for age34.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    'rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv',
    'rtl/qwen_sys/split_20261014/qkd_ectl3_epoch_direct_s.sv',
    'rtl/qwen_sys/split_20261014/qkd_ectl_a_tp8_epoch_direct.sv',
    'rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
]

def compile_calendar(context, row_latency, consume_age):
    if not 1 <= context <= 8192 or row_latency < 1 or not 1 <= consume_age <= 65535:
        raise ValueError('unsupported context/latency/age')
    # FP32 Q has 32 beats; last beat must have reached qcnt before first issue.
    if consume_age < 34:
        raise ValueError('Q is unavailable on the reserved consume edge')
    engines = []
    for stack in range(4):
        ns = (context >> 9) * 128 + min(128, max(0, (context & 511) - stack * 128))
        for engine in range(8):
            slots = []
            limit = 2048 if ns > 1024 else ns
            for scan, idx in enumerate(range(engine, limit, 8)):
                pidx = ((idx & 2048) | ((idx & 960) << 1) | ((idx & 1024) >> 4) | (idx & 63)) if ns > 1024 else idx
                if pidx >= ns:
                    continue
                slots.append(dict(t=((pidx >> 7) << 9) | (stack << 7) | (pidx & 127),
                                  request=4 + scan, write=7 + row_latency + scan,
                                  read=consume_age + scan - 1, consume=consume_age + scan))
            events = {}
            for slot in slots:
                if slot['write'] >= slot['read']:
                    raise ValueError(f'engine {stack}:{engine}: SRAM read precedes write visibility')
                for kind in ['write', 'consume']:
                    events.setdefault(slot[kind], []).append(kind)
            occupancy = high = 0
            for edge, kinds in sorted(events.items()):
                if 'consume' in kinds and occupancy == 0:
                    raise ValueError(f'engine {stack}:{engine}: underflow at {edge}')
                occupancy += kinds.count('write') - kinds.count('consume')
                high = max(high, occupancy)
                if not 0 <= occupancy <= 128:
                    raise ValueError(f'engine {stack}:{engine}: ring capacity at {edge}')
            assert occupancy == 0
            engines.append(dict(stack=stack, engine=engine, rows=len(slots),
                                max_occupancy=high, slots=slots))
    assert sum(e['rows'] for e in engines) == context
    return dict(schema='qwen-tp8-static-qk-calendar-v1', scope='native ECTL3 QK component; external service latency is a required implemented input; excludes ASTK/physical clock/native chip qualification',
                context=context, external_row_latency=row_latency, QK_ISSUE_AGE=consume_age,
                ROW_RETURN_LAT=row_latency + 5, LANE_D=4, capacity=128,
                sources={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}, engines=engines)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--context', type=int, default=8192)
    p.add_argument('--row-latency', type=int, required=True)
    p.add_argument('--consume-age', type=int, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = compile_calendar(args.context, args.row_latency, args.consume_age)
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')

if __name__ == '__main__':
    main()
