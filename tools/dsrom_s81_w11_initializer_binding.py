"""Typed initializer cost and finite same-port startup for selected W11.

No engine emitted. Existing owner83 and W6 coded-word widths are retained;
the operation bit uses a spare protected payload bit. Namespace comparators
and their registered reductions are positively charged, never timer-qualified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/dsrom_s81_w11_initializer_binding_20261004/model.json'


def tree(n):
    count = 0
    while n > 1:
        n = math.ceil(n / 8)
        count += n
    return count


def build(root=ROOT):
    root = Path(root)
    base = root / 'results/uarch/dsrom_s81_minimum_protected_group_20261004'
    src = root / 'results/uarch/dsrom_s81_allcopy_group_20261004/model.json'
    previous = json.loads(src.read_text())
    old = json.loads((base / 'model.json').read_text())
    measured = json.loads((base / 'evidence/selected_held_landing/record.json').read_text())
    prices = {k: v['SS']['area_um2'] for k, v in json.loads((base / 'inputs/cell_prices.json').read_text())['facts'].items()}
    # Twelve full-copy operation comparators shared between exclusive commit /
    # verify windows. Two bank receipt and two returned-capture comparators,
    # plus two receipt and two returned-capture registered reductions.
    leaf_replicas = 12 + 2 + 2 + 2 + 2
    counts = {k: n * leaf_replicas for k, n in measured['results']['equal83']['cell_counts'].items()}
    # Two extra serial stages per bank (receipt and returned-capture reduction).
    tags = 2 * 2 * 144
    counts['DFFHQNx1_ASAP7_75t_R'] = counts.get('DFFHQNx1_ASAP7_75t_R', 0) + tags
    counts['INVx1_ASAP7_75t_R'] = counts.get('INVx1_ASAP7_75t_R', 0) + tags
    flags = 2 * 2 * 3
    counts['DFFASRHQNx1_ASAP7_75t_R'] = counts.get('DFFASRHQNx1_ASAP7_75t_R', 0) + flags
    counts['INVx1_ASAP7_75t_R'] += flags
    added_ff = counts.get('DFFHQNx1_ASAP7_75t_R', 0) + counts.get('DFFASRHQNx1_ASAP7_75t_R', 0)
    prior_ff = old['slot']['FF_total_sinks'] + previous['area']['incremental_native_cell_counts']['DFFHQNx1_ASAP7_75t_R'] + previous['area']['incremental_native_cell_counts']['DFFASRHQNx1_ASAP7_75t_R']
    clock_buf = tree(prior_ff + added_ff) - tree(prior_ff)
    reset_buf = tree(old['area']['pipeline_valid_ASR_coded_FF'] + 24 + flags) - tree(old['area']['pipeline_valid_ASR_coded_FF'] + 24)
    body = sum(prices[k] * n for k, n in counts.items()) + (clock_buf + reset_buf) * prices['BUFx4_ASAP7_75t_R'] + flags * .04374
    # Copy operation check runs parallel to chunk equality, and its flag enters
    # the already charged match reduction. Receipt / reverse reductions add
    # one edge each. The counted fast owner-match gets a separate extra edge.
    field_local, count_fast, reverse_slow = 19, 10, 8
    # Cold-empty init bypasses old read/decode/equality/merge (eight edges).
    # It still encodes, writes, checked-readbacks, compares, and returns debt.
    init_local = field_local - 8
    def service(local):
        occupation = local / .9 + count_fast / 1.2 + reverse_slow / .9
        ii = math.ceil(occupation * .9)
        ingress = previous['service']['admission_gear_ns_bound'] + previous['service']['route_latency_ns_bound']
        return {'local_slow_edges': local, 'counted_fast_edges': count_fast,
                'reverse_slow_edges': reverse_slow, 'occupied_ns': occupation,
                'bank_service_II_slow_edges': ii, 'bank_service_II_ns': ii / .9,
                'active_capacity_per_bank': 1, 'empty_head_retirement_ns': ingress + occupation,
                'three_predecessor_retirement_ns': ingress + occupation + 3 * ii / .9}
    init = service(init_local)
    width, height = previous['slot']['outline_um']
    annex = math.ceil((2 * body / width) / .27) * .27
    paths = [src, base / 'model.json', base / 'evidence/selected_held_landing/record.json', base / 'inputs/cell_prices.json',
             root / 'tools/dsrom_s81_w11_control_scaffold.py', root / 'tools/templates/dsrom_s81_w11_publication_control_pkg.sv.in',
             root / 'tools/dsrom_s81_w11_initializer_binding.py']
    pins = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return {'candidate': previous['candidate'] + '-TYPEDINIT', 'source_pins': pins,
            'targets_GHz': {'bank': .9, 'count_receiver': 1.2, 'reverse_receiver': .9},
            'interface': {'owner_bits': 83, 'separate_init_operation_bits': 1,
                          'active_raw_bits': 101, 'receipt_raw_bits': 105,
                          'active_coded_bits': 144, 'receipt_coded_bits': 144,
                          'owner_tag_with_kind_raw_bits': 84, 'owner_tag_coded_bits': 144,
                          'route_payload_with_kind_bits': 137, 'route_coded_bits': 216,
                          'spare_payload_bit_must_be_encoded_and_checked': True},
            'ports': previous['ports'], 'field_service': service(field_local), 'initializer_service': init,
            'startup': {'reserved_rows_per_bank': 4, 'banks_parallel': 2,
                        'one_group_eight_rows_ns_bound': 4 * init['bank_service_II_ns'] + previous['service']['admission_gear_ns_bound'] + previous['service']['route_latency_ns_bound'],
                        'one_group_all512_rows_ns_bound': 256 * init['bank_service_II_ns'] + previous['service']['admission_gear_ns_bound'] + previous['service']['route_latency_ns_bound'],
                        'no_free_across_group_concurrency': True,
                        'cold_empty_fullrow_owner_required': True,
                        'all6_checked_return_before_GO': True,
                        'received_mask_unchanged_by_initialization': True,
                        'existing_live_row_must_not_be_zeroed': True},
            'cost': {'added_equal83_leaf_instances': leaf_replicas, 'added_cells': counts,
                     'added_clock_BUF': clock_buf, 'added_reset_BUF': reset_buf,
                     'added_body_um2': body, 'added_logic50_mm2': 2 * body / 1e6,
                     'macro_plus_logic50_mm2': previous['area']['macro_plus_logic50_mm2'] + 2 * body / 1e6,
                     'no_macro_or_4896_control_recharge': True, 'no_2184_replacement_credit': True},
            'slot': {'name': 'W11_MINIMUM_ALL6OLD_TYPEDINIT_LOCAL', 'outline_um': [width, height + annex],
                     'actual_parent_home': None, 'unblocked_tracks': None},
            'limits': {'loaded_namespace_path_measured': False, 'candidate_not_measured_group_II': True,
                       'engine_RTL_emitted': False, 'context_SS_FF': False, 'physical_fit': None,
                       'absolute_consumer_deadline': None, 'token_rate': None}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + '\n'
    if args.verify:
        if (ROOT / OUT).read_text() != text:
            raise SystemExit('initializer replay mismatch')
    elif args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
