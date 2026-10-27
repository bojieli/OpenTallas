#!/usr/bin/env python3
"""Compile legitimate layer entry inputs into native XR target-5 row writes.

Only io/h_in, io/pre_in and checkpoint attn_norm weights are read. No operation
result is used as a producer input. Dates, actual transport landing and caller
adoption remain explicit obligations; this is not a complete entry programme.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(Path(__file__).parent)]
import dv_layer_compile as D
import leaf_rows as LR
from lower_head import row_write_body


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_inputs(die, fixtures):
    fixtures = Path(fixtures)
    files = json.loads((fixtures / 'files.json').read_text())
    source = {}

    def read(name):
        spec = files[name]
        path = fixtures / name
        actual = sha(path)
        if actual != spec['sha256']:
            raise ValueError('fixture input source hash mismatch: ' + name)
        source[name] = dict(sha256=actual, dtype=spec['dtype'], shape=spec['shape'])
        return np.frombuffer(path.read_bytes(), dtype=np.dtype(spec['dtype'])).reshape(spec['shape'])

    h = read('io/h_in.bin')
    pre = read('io/pre_in.bin')
    gains = read('weights/attn_norm.bin')
    if h.dtype != np.dtype('float32') or h.shape != (4, 5120):
        raise ValueError('entry H requires exact FP32 container of four BF16 HC copies, D5120')
    if pre.dtype != np.dtype('float32') or pre.shape != (4,):
        raise ValueError('entry delayed pre requires four FP32 coefficients')
    hb = h.view(np.uint32)
    if np.any(hb & 65535):
        raise ValueError('entry H contains non-BF16 values: refuse implicit input truncation')
    if files['weights/attn_norm.bin'].get('format') != 'BF16' or gains.dtype != np.dtype('uint8') or gains.shape != (5120, 2):
        raise ValueError('attn norm checkpoint gain requires 5120 raw little-endian BF16 values')
    gain_bits = gains.copy().view('<u2').reshape(5120).astype(np.uint32) << 16
    pre_word = sum(int(v) << (32*k) for k, v in enumerate(pre.view(np.uint32)))
    slices = die.slices()
    by_sid = {v['sid']: k for k, v in slices.items()}
    if len(by_sid) != 16 or sorted(by_sid) != list(range(16)):
        raise ValueError('entry image requires exactly one actual slice for each SID0..15')
    writes, readers = [], []

    def emit(sid, leaf, row, data, region, element_map):
        if not 0 <= row < LR.LEAF_ROWS or not 0 <= data < 1 << 128:
            raise ValueError('entry native row overflow')
        payload = D.ctl_payload(1 << sid, 5, 1 << leaf, row_write_body(row, data))
        writes.append(dict(slice=by_sid[sid], sid=sid, leaf=leaf, row=row, region=region,
                           data128=f'{data:032x}', ctl_payload186=f'{payload:047x}', elements=element_map,
                           engine='VN' if by_sid[sid].endswith('N') else 'VS'))

    for sid in range(16):
        for leaf in range(5):
            start = 320*sid + 64*leaf
            # VP HLOAD combines rows2*i and2*i+1 as {odd128,even128}.
            # VN half-row packs BF16 lane4*half+l of copyc at16*(4*c+l).
            for sub in range(8):
                for half in range(2):
                    words = [int(hb[c, start+8*sub+4*half+l] >> 16)
                             for c in range(4) for l in range(4)]
                    packed = sum(w << (16*i) for i, w in enumerate(words))
                    for bank in range(2):
                        row = 2*(2*sub+half) + bank
                        emit(sid, leaf, row, (packed >> (128*bank)) & ((1<<128)-1), 'H',
                             dict(subbeat=sub, half=half, halfrow_bank=bank, global_start=start+8*sub+4*half))
            for row in range(16):
                data = sum(int(gain_bits[start+4*row+w]) << (32*w) for w in range(4))
                emit(sid, leaf, 64+row, data, 'GAIN', dict(global_start=start+4*row))
            emit(sid, leaf, LR.GU_ROWS['ffn'], pre_word, 'ENTRY_PRE', dict(source='io/pre_in.bin'))
            readers.append(dict(slice=by_sid[sid], leaf=leaf, hload_a0=0, gain_a0=64,
                                normr_a0=LR.GU_ROWS['ffn'], global_beat=5*sid+leaf))
    identities = [(w['sid'], w['leaf'], w['row']) for w in writes]
    if len(set(identities)) != len(writes):
        raise ValueError('entry native image aliases a leaf row')
    return dict(schema='opentallas.s81.entry_input_rows.v1', status='PARTIAL',
        die_sha256=die.die_sha, fixture_meta_sha256=sha(fixtures/'meta.json'), input_sources=source,
        writes=writes, readers=readers, row_count=len(writes),
        provenance='legitimate layer input h/pre and checkpoint norm gains; no ops output injection',
        lifetimes=[dict(region='H0..31', writer='entry target5', reader='VP HLOAD a0=0',
                        release='after actual HLOAD finishes; VN owns residual H thereafter'),
                   dict(region='GAIN64..79', writer='entry target5', reader='VP GAIN a0=64',
                        release='after actual GAIN finishes; do not overlap VPX writes'),
                   dict(region='GU_FFN1008', writer='entry target5 delayed pre', reader='attn NORMR a0=1008',
                        release='after final attn NORMR read; current FFN HC overwrites only later')],
        runtime_program_bound=False, landing_dates_qualified=False, full_stage=False, full_token=False,
        obligations=['adopt these native writes in real host/walker jobs with immutable dates',
                     'bind actual XR target5 -> downlink -> VP store commit ages before HLOAD/GAIN/NORMR',
                     'compile sixteen-slice NX root and XQ gather exchange from real current source paths'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree', type=Path, required=True)
    ap.add_argument('--fixtures', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError('preserve existing entry artifact; select a fresh --out')
    data = compile_inputs(D.Die(a.tree), a.fixtures)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, indent=1)+'\n')
    print('ENTRY_INPUT_ROWS', data['row_count'], 'PARTIAL: native programme landing/adoption and collective calendar remain unbound')


if __name__ == '__main__':
    main()
