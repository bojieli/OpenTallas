"""Additive all-copy validation successor; preserves the copy-0 predecessor.

Reuse measured held equal83 cells as a conservative padded comparator. Four
parallel chunks cover a decoded 256-bit row; a second held equal83 compares
the four match bits against ones. No unmeasured wide equality is one edge.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/uarch/dsrom_s81_minimum_protected_group_20261004'
OUT = 'results/uarch/dsrom_s81_allcopy_group_20261004'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(n):
    count = 0
    while n > 1:
        n = math.ceil(n / 8)
        count += n
    return count


def equal256(a, b):
    if not (0 <= a < 1 << 256 and 0 <= b < 1 << 256):
        raise ValueError('decoded row width')
    # Exactly four chunks, including the final seven-bit partial chunk.
    return all(((a >> i) & ((1 << 83) - 1)) ==
               ((b >> i) & ((1 << 83) - 1)) for i in (0, 83, 166, 249))


def qualified_images(images, expected=None):
    if len(images) != 6:
        raise ValueError('all six copies required')
    target = images[0] if expected is None else expected
    return all(equal256(image, target) for image in images)


def build(root=ROOT):
    root = Path(root)
    ns = root / BASE
    paths = ['model.json', 'inputs/cell_prices.json',
             'evidence/selected_held_landing/record.json',
             'inputs/publication_control.json', 'inputs/check_macro.json']
    source = {str(ns.relative_to(root) / p): sha(ns / p) for p in paths}
    source['tools/dsrom_s81_allcopy_group.py'] = sha(root / 'tools/dsrom_s81_allcopy_group.py')
    macro_dir = Path('physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2')
    for suffix in ('.json', '.v', '.lef', '_ss.lib', '_ff.lib'):
        name = macro_dir / ('ot_sram_1rw_256x64_m4_r2c2' + suffix)
        source[str(name)] = sha(root / name)
    read = lambda p: json.loads((ns / p).read_text())
    old = read('model.json')
    record = read('evidence/selected_held_landing/record.json')
    eq = record['results']['equal83']
    cut = old['mutable_codec']['cuts']['equal83']
    if cut['serial_held_edges'] != 1 or any(
            eq['timing'][c]['electrical_violations'] for c in ('ss', 'ff')):
        raise ValueError('retained comparator no longer supports selected cut')
    price = {k: v['SS']['area_um2'] for k, v in
             read('inputs/cell_prices.json')['facts'].items()}
    # Reuse the same validator for old and postverify windows, capacity one.
    # Provision six expected-image comparisons per bank, even though old-read
    # only needs five versus copy0. Full 83-bit leaf charge, no padding credit.
    replicas = 2 * 6 * (4 + 1)
    counts = {cell: count * replicas for cell, count in eq['cell_counts'].items()}
    # Four extra serial stages, two banks, full coded144 tags at each cut.
    tag_ff = 4 * 2 * 144
    counts['DFFHQNx1_ASAP7_75t_R'] = counts.get('DFFHQNx1_ASAP7_75t_R', 0) + tag_ff
    counts['INVx1_ASAP7_75t_R'] = counts.get('INVx1_ASAP7_75t_R', 0) + tag_ff
    # Three-copy coded valid per stage/bank, explicit async reset and ties.
    valid_ff = 4 * 2 * 3
    counts['DFFASRHQNx1_ASAP7_75t_R'] = counts.get('DFFASRHQNx1_ASAP7_75t_R', 0) + valid_ff
    counts['INVx1_ASAP7_75t_R'] += valid_ff
    added_ff = counts.get('DFFHQNx1_ASAP7_75t_R', 0) + counts.get('DFFASRHQNx1_ASAP7_75t_R', 0)
    old_ff = old['slot']['FF_total_sinks']
    clock_buffers = tree(old_ff + added_ff) - tree(old_ff)
    reset_buffers = tree(old['area']['pipeline_valid_ASR_coded_FF'] + valid_ff) - tree(old['area']['pipeline_valid_ASR_coded_FF'])
    body = sum(price[c] * n for c, n in counts.items())
    body += (clock_buffers + reset_buffers) * price['BUFx4_ASAP7_75t_R'] + valid_ff * .04374
    stages = []
    edge = 0
    for s in old['calendar']:
        stages.append(dict(s, begin_edge=edge, end_edge=edge + s['occupied_edges']))
        edge += s['occupied_edges']
        if s['stage'] in ('old_decode', 'postverify_decode'):
            prefix = 'old' if s['stage'] == 'old_decode' else 'postverify'
            for name in ('allcopy_chunk_equal', 'allcopy_match_reduce'):
                stages.append({'stage': prefix + '_' + name,
                               'begin_edge': edge, 'end_edge': edge + 1,
                               'occupied_edges': 1, 'domain': 'serial_0.9_target'})
                edge += 1
    service = dict(old['service'])
    occupied = edge / .9 + service['counted_return_fast_edges'] / 1.2 + service['reverse_release_slow_edges'] / .9
    ii = math.ceil(occupied * .9)
    service.update(local_RMW_edges=edge, local_RMW_ns=edge / .9,
                   occupied_bank_ns_bound=occupied, bank_service_II_slow_edges=ii,
                   bank_service_II_ns=ii / .9,
                   accepted_head_to_captured_retirement_ns_bound=service['admission_gear_ns_bound'] + service['route_latency_ns_bound'] + occupied,
                   maximum_payload_write_bytes_per_slow_edge_average=64 / ii)
    queued = dict(service, rows_ahead_bound=3, predecessor_wait_ns=3 * ii / .9)
    queued['accepted_head_to_captured_retirement_ns_bound'] += queued['predecessor_wait_ns']
    width = old['slot']['outline_um'][0]
    # Widen annex only; never consume the two existing signal/PG corridors.
    extra_height = math.ceil((2 * body / width) / .27) * .27
    return {
        'candidate': old['candidate'] + '-ALL6OLD',
        'source_pins': source,
        'target_GHz': .9, 'qualified_clock': False,
        'ports': {'old_read': 'all6 data/check copies in parallel, exclusive 1RW window',
                  'write': 'all6 data/check copies, same checked merged image',
                  'postverify': 'all6 data/check copies versus held expected image',
                  'decoder_ports_reused_old_post': 48, 'encoder_ports': 8,
                  'macro_instances_unchanged': 24,
                  'no_other_accepted_access_debt_before_GO': True,
                  'RMW_requires_ld_run_and_sm_run_ended_and_expected_mask_complete': True},
        'validator': {'measured_leaf': 'equal83', 'physical_leaf_replicas': replicas,
                      'chunks_per256': 4, 'serial_stages_per_window': 2,
                      'reuse_old_postverify': True,
                      'held_decode_outputs_and_expected_merge_output_required': True,
                      'intrinsic_SS_remaining_wire_ps_after25skew': cut['serial_remaining_wire_ps_after25skew'],
                      'intrinsic_FF_hold_ps_after25unc25skew': cut['FF_hold_ps_after25unc_and25adverse_skew'],
                      'loaded_full_validator_and_enable_not_measured': True},
        'calendar': stages, 'service': service, 'WQD4_max_service': queued,
        'check_macro_timing': old['macro_corners']['check'],
        'check_macro_clock_load_fF': {'ss': 12 * old['macro_corners']['check']['ss']['clk_cap_ff'],
                                    'ff': 12 * old['macro_corners']['check']['ff']['clk_cap_ff']},
        'area': {'incremental_native_cell_counts': counts, 'incremental_clock_BUF': clock_buffers,
                 'incremental_reset_BUF': reset_buffers, 'incremental_body_um2': body,
                 'incremental_logic50_mm2': 2 * body / 1e6,
                 'macro_plus_logic50_mm2': old['area']['macro_plus_logic50_mm2'] + 2 * body / 1e6,
                 'controller4896_already_in_predecessor': True,
                 'no_2184_rawqueue_credit_claimed': True,
                 'no_r4_or_macro_recharge': True},
        'slot': {'name': 'W11_MINIMUM_ALL6OLD_LOCAL',
                 'outline_um': [width, old['slot']['outline_um'][1] + extra_height],
                 'extra_annex_height_um': extra_height, 'actual_parent_home': None,
                 'actual_unblocked_tracks': None},
        'initialization': {'simulation_zero_not_provenance': True,
                           'actual_init_owner_and_allcopy_checked_image_required': True,
                           'startup_service_not_in_row_service': True,
                           'typed_init_control_delta_not_yet_joined': True},
        'limits': {'engine_RTL_admitted': False, 'physical_fit': None,
                   'context_SS_FF': False, 'absolute_consumer_deadline': None,
                   'token_latency_delta': None,
                   'counted_receipt_requires_actual_reverse_accept_and_capture': True,
                   'original_copy0_model_unchanged': True}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + '\n'
    if args.verify:
        if (ROOT / OUT / 'model.json').read_text() != text:
            raise SystemExit('model replay mismatch')
    elif args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
