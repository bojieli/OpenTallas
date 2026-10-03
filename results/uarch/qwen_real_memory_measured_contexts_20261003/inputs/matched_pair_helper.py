"""Price matched frozen REAL_MEM observations; no simulation or token-rate grant."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = 'results/rtl/qwen_rom_real_memory_20261003/frozen_v2/'
OUTPUT = 'results/uarch/qwen_rom_real_memory_calibration_20261003/model.json'
MATCH = ('source_sha256', 'binary_sha256', 'generated_core_sha256', 'stage_image_sha256',
         'kv_history_sha256', 'oracle_json_sha256', 'design_point', 'wire_stages')


def matched_pair(ideal, real, position):
    for run in (ideal, real):
        if (run['position'] != position or run['status'] != 'pass' or run['returncode'] != 0
                or run['source_stable'] is not True or run['stages_run'] != ['E', 'L0', 'L1', 'L2']):
            raise ValueError('incomplete, failed, drifted or differently scoped run')
        if len(run['source_sha256']) != 46:
            raise ValueError('complete 46-source identity required')
        expected = {f'{stage}_die{die}_x' for stage in ('E', 'L0', 'L1', 'L2') for die in range(4)}
        if set(run['layer_x_checks']) != expected:
            raise ValueError('complete named stage/die output identities required')
        if any(x['mismatches'] != 0 or x['first_mismatch'] is not None
               for x in run['layer_x_checks'].values()) or len(run['layer_x_checks']) != 16:
            raise ValueError('all four dies and three layers plus embedding must be exact')
    for key in MATCH:
        if not ideal[key] or ideal[key] != real[key]:
            raise ValueError(f'matched A/B identity mismatch: {key}')
    if any(ideal['layer_x_checks'][k]['actual_sha256'] != real['layer_x_checks'][k]['actual_sha256']
           for k in ideal['layer_x_checks']):
        raise ValueError('actual produced outputs differ in matched A/B')
    for layer in ('L0', 'L1', 'L2'):
        for die in range(4):
            key = f'{layer}_die{die}'
            check = real['token_kv_writeback_checks'][key]
            if (check['k_codes'], check['v_codes'], check['k_mismatches'], check['v_mismatches']) != (256, 256, 0, 0):
                raise ValueError('actual KV writeback not exact and complete')
    if 'KV_IDEAL' not in ideal['configuration'] or 'REAL_MEM' not in real['configuration']:
        raise ValueError('explicit ideal/real service selection required')
    rows = []
    for layer in ('L0', 'L1', 'L2'):
        before, after = ideal['stages'][layer]['cycles'], real['stages'][layer]['cycles']
        if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in (before, after)):
            raise ValueError('positive integer cycle observations required')
        delta = after - before
        if delta < 0:
            raise ValueError('new negative memory delta requires review, not silent gain adoption')
        rows.append(dict(position=position, layer=layer, ideal_cycles=before, real_cycles=after,
                         observed_memory_service_extra_cycles=delta,
                         overhead_percent=100 * delta / before,
                         functional_CLK_PS=833,
                         functional_extra_us=delta * 833 / 1e6,
                         real_memory_max_over_dies=real['stages'][layer].get('memory_max_over_dies', {}),
                         real_memory_counters=real['stages'][layer].get('memory', {})))
    return rows


def build(root=ROOT):
    root = Path(root)
    rows, pairs, pins = [], [], {}
    source = None
    for position in (0, 255):
        runs = []
        for mode in ('ideal', 'real'):
            name = f'{INPUT}runs/{mode}2_p{position}.json'
            data = (root / name).read_bytes()
            pins[name] = hashlib.sha256(data).hexdigest()
            runs.append(json.loads(data))
        ideal, real = runs
        rows.extend(matched_pair(ideal, real, position))
        if source is not None and source != ideal['source_sha256']:
            raise ValueError('P0/P255 source collections differ')
        source = ideal['source_sha256']
        sums = [sum(x['stages'][k]['cycles'] for k in ('L0', 'L1', 'L2')) for x in runs]
        pairs.append(dict(position=position, matched_identity={k: ideal[k] for k in MATCH},
            layer_sum_ideal_cycles=sums[0], layer_sum_real_cycles=sums[1],
            layer_sum_extra_cycles=sums[1] - sums[0],
            observed_run_total_ideal_cycles=ideal['total_cycles'],
            observed_run_total_real_cycles=real['total_cycles'],
            unattributed_tail_cycles={mode: run['total_cycles'] - sum(stage['cycles'] for stage in run['stages'].values())
                                      for mode, run in zip(('ideal', 'real'), runs)},
            actual_real_service=real['memory_services']))
    pins['tools/qwen_rom_real_memory_calibration.py'] = hashlib.sha256((root / 'tools/qwen_rom_real_memory_calibration.py').read_bytes()).hexdigest()
    return dict(schema='opentallas.qwen-rom.matched-real-memory-calibration.v1',
        status='MEASURED_FUNCTIONAL_THREE_LAYER_SERVICE_CALIBRATION', rows=rows, pairs=pairs,
        observed_layer_overhead_percent=dict(low=min(x['overhead_percent'] for x in rows),
                                            high=max(x['overhead_percent'] for x in rows)),
        old_compute_baseline_cycles=4668,
        old_compute_baseline_transfer='REFUSED: matched ideal baseline is 4804/4828 with different source/calibration identity',
        full_token_memory_price_us=None, full_token_rate=None, posted_write_gain=None,
        physical_clock_credit=False, adoption=False,
        composition_rule='Use the delta only for the same source/design/position/layer and memory-service identity; never add it atop KV delivery already charged by a calendar.',
        counter_rule='per-die maxima and overlapping stalls are diagnostics, not additive latency terms',
        limitations=['P0/P255 L0..L2 only, no full-token or physical qualification',
                     'P1023 REAL_MEM not enrolled; completed ideal-only data cannot give an A/B delta',
                     'CLK_PS833 converts functional cycles only, not SS/FF clock closure',
                     'no uniform percentage extrapolation to 36 layers or 8K context',
                     'no posted-write reduction until an actual matched run'], input_sha256=pins)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / OUTPUT)
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    payload = json.dumps(build(), indent=2, sort_keys=True) + '\n'
    if args.verify:
        if args.out.read_text() != payload:
            raise ValueError('calibration record drift; preserve old evidence and regenerate successor')
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload)
    print('PASS matched P0/P255 six layers; no token or posted-write gain credit')


if __name__ == '__main__':
    main()
