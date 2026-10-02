import copy
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('r49join', Path(__file__).resolve().parents[1] / 'tools/dsrom_I66_R49_service_join.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def test_reviewed_contract_keeps_three_distinct_boundaries():
    h, p = M.load()
    j = M.join(h, p)
    assert [j[k] for k in ('conditional_first_attempt_packet_ACK_bound_edges',
                           'conditional_final_home_visibility_edge',
                           'conditional_last_packet_debt_edge')] == [2931, 13480, 17495]
    assert j['actual_consumer_deadline'] is None
    assert not j['new_jobs']


@pytest.mark.parametrize('mutation', ['ack_early', 'credit_early', 'visibility_ack', 'CDC_transfer',
                                     'old_collision', 'crossdie', 'measured_transfer', 'false_origin',
                                     'default_timeout', 'bool_edge', 'feedback_forward'])
def test_invalid_causal_or_physical_transfer_rejected(mutation):
    h, p = copy.deepcopy(M.load())
    if mutation == 'ack_early': p['calendar']['packets'][0]['matching_positive_ACK_seen'] -= 1
    if mutation == 'credit_early': p['calendar']['packets'][1]['first_collect'] -= 1
    if mutation == 'visibility_ack': p['ownership']['delivery_ACK_is_not_destination_visibility'] = False
    if mutation == 'CDC_transfer': p['spatial']['CDC_FIFO_adequacy_and_clock_ratio_qualified'] = True
    if mutation == 'old_collision': h['corrected_common_bbox_DBU'][0] -= 52164
    if mutation == 'crossdie': h['per_shard_raw_homes'][1]['actual_physical_shard_die'] = 0
    if mutation == 'measured_transfer': p['service_bound_contract']['actual_service_accepts_measured'] = True
    if mutation == 'false_origin': p['calendar']['actual_source_indexed_owner_response_edge'] = 10
    if mutation == 'default_timeout': p['timeout']['proposed_ACK_TIMEOUT'] = 1024
    if mutation == 'bool_edge': p['calendar']['packets'][3]['flits'] = True
    if mutation == 'feedback_forward': h['forward_payload_does_not_traverse_feedback_BUFs'] = False
    with pytest.raises(ValueError): M.join(h, p)
