"""Reviewed R49/provider metadata join. No RTL, observed trace, or launch authority."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_I66_R49_service_join_20261002'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value):
    require(type(value) is int and value > 0, 'positive integer edge count required')
    return value


def load():
    pins = json.loads((BASE / 'input_pins.json').read_text())
    result = []
    for name in ('home', 'provider'):
        data = (BASE / 'inputs' / (name + '.json')).read_bytes()
        require(hashlib.sha256(data).hexdigest() == pins[name]['sha256'], 'input pin mismatch')
        result.append(json.loads(data))
    return result


def join(home, provider):
    require(home['total_exact_seats'] == 576, 'exact seats required')
    require(home['no_combinational576way_crossdie_mux'] is True, 'no cross-die mux')
    require(home['common_circuit_home_shard'] is None, 'common owner not yet selected')
    require(home['physical_fit_proven'] is False and home['physical_build_admitted'] is False,
            'model geometry is not physical admission')
    raw = sorted(home['per_shard_raw_homes'], key=lambda x: x['shard'])
    require([(x['actual_physical_shard_die'], x['seats']) for x in raw] == [(0, 320), (1, 256)],
            'physical shard ownership')
    common = home['corrected_common_bbox_DBU']
    gaps = [common[0] - x['bbox_DBU'][2] for x in raw]
    require(gaps == [4320, 4320], 'R49 common gap')
    require(home['forward_payload_does_not_traverse_feedback_BUFs'] is True,
            'feedback buffers cannot become forward repair')
    require(home['source_typed_feedback_hold_closed'] is False and home['forward_hold_closed'] is False,
            'typed screen is not hold closure')
    contract = provider['service_bound_contract']
    space = provider['spatial']
    require(contract['actual_service_accepts_measured'] is False, 'no measured service transfer')
    require(provider['selected_for_RTL'] is False and provider['physical_build_admitted'] is False,
            'no provider RTL admission')
    require(space['CDC_FIFO_adequacy_and_clock_ratio_qualified'] is False,
            'CDC needs actual implementation qualification')
    require(provider['ownership']['delivery_ACK_is_not_destination_visibility'] is True,
            'packet ACK cannot substitute for home visibility')
    require(provider['ports']['packet_credit'] == 1, 'sole packet credit source contract')
    forward = positive(space['forward_route_CDC_PHY_envelope_edges'])
    reverse = positive(space['reverse_route_CDC_PHY_envelope_edges'])
    packets = provider['calendar']['packets']
    previous = {}
    waits = []
    for p in packets:
        n = positive(p['flits']); require(n <= 256, 'whole packet RX capacity')
        start = positive(p['first_collect'])
        link = positive(p['link_II']); delivery = positive(p['delivery_II'])
        direction = 'return' if p['kind'] in ('result_rows', 'owner_completion') else 'forward'
        if direction in previous:
            require(start >= previous[direction] + 1, 'packet credit reused before matching ACK')
        last_collect = start + n - 1
        first_send = last_collect + 1
        last_send = first_send + (n - 1) * link
        last_receive = last_send + forward
        first_deliver = last_receive + 1
        last_deliver = first_deliver + (n - 1) * delivery
        ack = last_deliver + 1 + reverse
        expected = dict(last_collect=last_collect, first_send=first_send, last_send=last_send,
                        first_receive=first_send + forward, last_receive=last_receive,
                        first_deliver=first_deliver, last_deliver=last_deliver,
                        matching_positive_ACK_seen=ack, next_packet_credit=ack + 1,
                        TX_WAIT_ACK_edges=ack - last_send)
        require(all(type(p[k]) is int and p[k] == v for k, v in expected.items()),
                'source store-forward/delivery/ACK recurrence')
        previous[direction] = ack
        waits.append(ack - last_send)
    timeout = provider['timeout']
    require(max(waits) == timeout['required_successful_max_edges'], 'packet bound mismatch')
    require(timeout['source_default'] < max(waits) <= timeout['proposed_ACK_TIMEOUT'],
            'default FAIL and proposal must remain separate')
    require(timeout['successful_bound_first_attempt_only'] is True, 'not arbitrary fault/stall bound')
    calendar = provider['calendar']
    result = next(p for p in packets if p['kind'] == 'result_rows')
    require(calendar['final_destination_visible'] == result['last_deliver'] + 1,
            'local post-NBA visibility recurrence')
    require(calendar['all_delivery_owner_debt_retired'] == max(p['matching_positive_ACK_seen'] for p in packets),
            'last packet debt bound')
    require(contract['successful_terminal_bound'] == calendar['all_delivery_owner_debt_retired'],
            'packet envelope terminal bound')
    require(calendar['actual_source_indexed_owner_response_edge'] is None and
            calendar['actual_source_input_producer_ready_edge'] is None,
            'template origin cannot become actual accepted origin')
    return {
        'scope': 'SOURCE_MODEL_JOIN_NOT_ACTUAL_SERVICE_OR_CURRENT_PROGRAM_CALIBRATION',
        'home_common_gap_um': 4.32, 'physical_shard_seats': [320, 256],
        'global_context_bits': 169, 'separate_physical_shard_bits': 1,
        'candidate_request_bits': 187, 'candidate_reply_bits': 240,
        'ABI_selected': False,
        'conditional_first_attempt_packet_ACK_bound_edges': max(waits),
        'conditional_final_home_visibility_edge': calendar['final_destination_visible'],
        'conditional_last_packet_debt_edge': calendar['all_delivery_owner_debt_retired'],
        'origin_rule': calendar['conditional_start_rule'],
        'reserved_resources': contract['reserve_before_GO'],
        'credits': {'wire_packet_per_direction': 1, 'root_seats_per_physical_shard': [320, 256],
                    'proposed_CDC_flits_per_direction': space['CDC_depth_flits_reserved'],
                    'gather_sink_seats': None, 'read_pipeline_outstanding': None},
        'required_distinct_observations': [
            'indexed owner response and input producer ready',
            'reserve sink seat before scalar read acceptance',
            'tagged row capture and physical shard',
            'last accepted packet delivery then matching packet ACK',
            'same-context ordered formatter output and actual home VM post-NBA visibility',
            'source healthy idle and all packet debts before context reuse',
            'actual consumer VM read and registered X tag in the same enrolled PHW10 journal'],
        'typed_paths': {
            'feedback': 'same-cell loop: storage QN -> restore -> two BUF -> feedback NAND -> final NAND -> storage D',
            'forward': 'capture write and scalar read/gather paths require separate typed source mapping; feedback-only BUFs excluded',
            'feedback_routed_hold_closed': False, 'forward_SS_FF_closed': False,
            'shared_restore_load_characterized': False},
        'physical_bindings_missing': [
            'common circuit physical shard and separate per-shard selector paths',
            'capture/read/gather/VM/consumer named pins, legal escapes, vias and route RC',
            'feedback BUF PG feeds and clock/reset ingress sites/load/skew/release',
            'CDC clock phase, FIFO adequacy, credits and named endpoints'],
        'actual_consumer_deadline': None, 'finite_actual_service': 'BOUND_MISSING',
        'physical_fit': False, 'hardware_admitted': False, 'full_token_qualified': False,
        'new_jobs': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(join(*load()), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
