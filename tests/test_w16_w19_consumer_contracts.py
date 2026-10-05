import copy
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w16_w19_consumer_contracts as C


def test_parent_inventory_agreement():
    C.parent_agreement(C.B.read(C.B.INVENTORY), C.B.read(C.VERIFY))


@pytest.mark.parametrize('change', ['group_dtype', 'hash', 'index', 'blob_claim', 'physical_claim'])
def test_parent_provenance_refusal(change):
    inv, parent = C.B.read(C.B.INVENTORY), copy.deepcopy(C.B.read(C.VERIFY))
    if change == 'group_dtype':
        parent['groups']['other_text_objects_unclassified']['dtype_bytes']['F32'] += 1
    elif change == 'hash':
        parent['inventory_sha256'] = '0' * 64
    elif change == 'index':
        parent['checkpoint_index_sha256'] = '0' * 64
    elif change == 'blob_claim':
        next(iter(parent['header_bindings'].values()))['full_blob_rehashed'] = True
    else:
        parent['physical_format_or_replication_qualified'] = True
    with pytest.raises(C.B.Refusal):
        C.parent_agreement(inv, parent)


def test_actual_consumers_do_not_supply_resident_replicas():
    ledger = C.build()
    families = ledger['source_tensor_families']
    assert ledger['parent_verified_headers'] == 44
    assert sum(f['tensors'] for f in families.values()) == 542
    assert sum(f['stored_bytes'] for f in families.values()) == 204240953808
    assert families['hc_attn_fn']['stored_bytes'] == 78643200
    assert len(families['hc_attn_fn']['reference_token_calls']) == 40
    assert all(call['ranks'] == 'all' for call in families['hc_attn_fn']['reference_token_calls'])
    assert families['attn.attn_sink']['reference_token_calls'][0]['ranks'] == 'heads'
    ratios = C.B.read(C.B.CONFIG)['metadata']['operator_config']['compress_ratios']
    for call in families['attn.indexer.wk.weight']['reference_token_calls']:
        group = 1048575 // ratios[call['layer']]
        assert call['ranks'] == [(group // 8) % 96]
    assert families['ffn.gate.bias_vl']['reference_function'] == 'unreferenced_in_AR_executor'
    assert families['embed.weight']['reference_function'] == 'host_input_lookup'
    assert all(f['resident_replica_count'] is None and f['hardware_consumer_contract'] is None
               and f['reservations'] is None for f in families.values())
    assert not ledger['full_fit'] and not ledger['adopted']
    assert ledger['measured_service_cycles'] is None


def test_unsupported_mapping_refused():
    for name in ('invented.norm.weight', 'hc_attn_invented', 'hc_ffn_invented'):
        with pytest.raises(C.B.Refusal, match='unsupported'):
            C.binding(name)


def test_roundtrip_and_pin_refusal():
    result = json.loads(json.dumps(C.build()))
    C.check(result)
    result['pins'][C.VERIFY] = '0' * 64
    with pytest.raises(C.B.Refusal, match='pin drift'):
        C.check(result)
