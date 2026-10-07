#!/usr/bin/env python3
"""S81 PQ full-shape design inputs from the actual 1792 mappings (Claude, 2026-10-07): BF beat adjacency and region
row bursts.

For every phase record of a matrix_map (hash-checked against the committed remote_hashes.json of
results/uarch/dsrom_s81_mixed1792_mapping_20261007) this computes:
  * the native spine stream (tools/dsrom_s81_target_field_controls.native_stream, the inventory's emitter): beats,
    valid beats, the longest run of back-to-back valid beats, and the exact extra lane cycles a two-cycle-per-BF-beat
    serial lane (option D / W3) costs: a greedy in-order schedule where every valid BF beat occupies two lane slots and
    an idle native slot absorbs one slot of accumulated delay (order of beats unchanged, spacing only grows);
  * rows per return region per phase (distinct row tags of the plans whose pair lies in the region; region bounds from
    the stage map), the burst that one root emits at <= 1 row / stream cycle.
Pure metadata: no weights, no RTL.
"""
import argparse
import gzip
import hashlib
import json
import sys
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
MAP = ROOT / 'results/uarch/dsrom_s81_mixed1792_mapping_20261007'
CASES = {'half': 'half_dedicated', 'full': 'full_shared'}
EMITTER = '8cfea7014a7513448455a612230b6e1fdda14f974f66fa4ee999a0d8ce3ba95e'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def serial_extra(beats):
    """extra lane cycles when each valid beat takes two slots (idle native slots absorb accumulated delay)"""
    d = mx = 0
    for b in beats:
        if b & 1:
            d += 1
            mx = max(mx, d)
        elif d:
            d -= 1
    return d, mx


def stats(case, mapping):
    from dsrom_s81_target_field_controls import native_stream
    want = json.loads((MAP / 'remote_hashes.json').read_text())[f'{CASES[case]}/matrix_map.jsonl.gz']
    if sha(mapping) != want:
        raise SystemExit(f'{case}: matrix_map hash mismatch (want {want})')
    sm = json.loads((MAP / CASES[case] / 'stage_map.json').read_text())
    cache, stages, ehash = {}, {}, None
    with gzip.open(mapping, 'rt') as f:
        for line in f:
            m = json.loads(line)
            if isinstance(m['plans'], str):
                m['plans'] = json.loads(m['plans'])
            s = m['stage']
            bounds = sm['region_bounds_by_stage'][s] if 'region_bounds_by_stage' in sm else sm['region_bounds']
            key = (m['format'], m['K'], tuple(map(tuple, m['segments'])), tuple(tuple(p[:5]) for p in m['plans']))
            if key not in cache:
                _, beats, ehash = native_stream(m)
                v = [b & 1 for b in beats]
                run = cur = 0
                for x in v:
                    cur = cur + 1 if x else 0
                    run = max(run, cur)
                adj = sum(1 for a, b in zip(v, v[1:]) if a and b)
                tail, peak = serial_extra(beats)
                cache[key] = dict(beats=len(beats), valid=sum(v), max_run=run, adjacent_pairs=adj,
                                  serial_extra_end=tail, serial_extra_peak=peak)
            c = cache[key]
            reg = {}
            for si, pair, first, count, stride, *_ in m['plans']:
                r = bisect_right(bounds, pair) - 1
                reg.setdefault(r, set()).update(first + j * stride for j in range(count))
            rmax = max(len(x) for x in reg.values())
            st = stages.setdefault(s, dict(phases=0, bf_phases=0, bf_beats=0, bf_valid=0, bf_max_run=0,
                                           bf_adjacent_pairs=0, bf_serial_extra_sum=0, bf_serial_extra_max=0, bf_serial_peak_max=0,
                                           q_beats=0, max_rows_region_phase=0, rows=0, max_phase_rows=0))
            st['phases'] += 1
            st['rows'] += m['rows']
            st['max_phase_rows'] = max(st['max_phase_rows'], m['rows'])
            st['max_rows_region_phase'] = max(st['max_rows_region_phase'], rmax)
            if m['format'] == 'bf16':
                st['bf_phases'] += 1
                st['bf_beats'] += c['beats']
                st['bf_valid'] += c['valid']
                st['bf_max_run'] = max(st['bf_max_run'], c['max_run'])
                st['bf_adjacent_pairs'] += c['adjacent_pairs']
                st['bf_serial_extra_sum'] += c['serial_extra_end']
                st['bf_serial_extra_max'] = max(st['bf_serial_extra_max'], c['serial_extra_end'])
                st['bf_serial_peak_max'] = max(st['bf_serial_peak_max'], c['serial_extra_peak'])
            else:
                st['q_beats'] += c['beats']
    if ehash != EMITTER:
        raise SystemExit('native emitter source changed: ' + str(ehash))
    S = list(stages.values())
    tot = lambda k: sum(x[k] for x in S)
    return dict(mapping_sha256=want, stages=len(S), phases=tot('phases'), bf_phases=tot('bf_phases'),
                bf_beats=tot('bf_beats'), bf_valid_beats=tot('bf_valid'),
                bf_max_back_to_back=max(x['bf_max_run'] for x in S), bf_adjacent_valid_pairs=tot('bf_adjacent_pairs'),
                bf_serial_extra_cycles_sum=tot('bf_serial_extra_sum'),
                bf_serial_extra_cycles_max_phase=max(x['bf_serial_extra_max'] for x in S),
                bf_serial_beat_delay_max=max(x['bf_serial_peak_max'] for x in S),
                bf_serial_extra_over_bf_beats=tot('bf_serial_extra_sum') / max(1, tot('bf_beats')),
                max_rows_region_phase=max(x['max_rows_region_phase'] for x in S),
                max_phase_rows=max(x['max_phase_rows'] for x in S), distinct_stream_patterns=len(cache),
                per_stage={str(k): v for k, v in sorted(stages.items())})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--half', type=Path, help='half_dedicated matrix_map.jsonl.gz')
    ap.add_argument('--full', type=Path, help='full_shared matrix_map.jsonl.gz')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    res = dict(schema='opentallas.s81.pq-stream-stats.v1', native_emitter_sha256=EMITTER,
               tool_sha256=sha(__file__))
    for case in ('half', 'full'):
        if getattr(a, case):
            res[case] = stats(case, getattr(a, case))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'per_stage'} for k, v in res.items()
                      if k in ('half', 'full')}, indent=1))


if __name__ == '__main__':
    main()
