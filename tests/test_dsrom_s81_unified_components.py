import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'tools/dsrom_s81_unified_components.py'
spec = importlib.util.spec_from_file_location('s81_components', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_r4_replaces_not_sums():
    x=m.build(ROOT)
    assert x['area']['VM_per_provider_floor_mm2'] == pytest.approx(7.17865226592)
    assert x['area']['one_capture_plus_one_VM_component_floor_mm2'] == pytest.approx(7.23848642808)
    assert x['clock_load']['additional_VM_FF_floor'] == 7798192


def test_exact_selected_inventory_and_no_unary_credit():
    x=m.build(ROOT)
    assert x['inventory']['total_dies']==368
    assert x['inventory']['total_layer_macros']==3132432
    assert x['return']['unary']==384
    assert x['return']['nodes']==5090
    assert x['inventory']['ROM_ECC'] is False
    assert x['service']['mutable_protection_retained'] is True


def test_no_clock_slot_rate_inheritance():
    x=m.build(ROOT)
    assert x['clock_load']['selected_VM_GHz'] is None
    assert x['area']['whole_die_fit'] is None
    assert x['latency']['AR_token_ns'] is None
    assert x['latency']['single_user_tokens_s'] is None
    assert not x['admission']['physical']
    assert x['latency']['selected_service']['bound_ns'] is None


def test_fault_suffix_and_capture_differ():
    x=m.build(ROOT)
    assert x['service']['whole_phase_slots']==9
    assert x['service']['capture_capacity_per_root']==1
    assert x['service']['accepted_phase_rows_bound']==4608
    assert x['service']['capture_no_READY']
    assert x['service']['no_next_GO_while_faulted']


def test_pipeline_exact_does_not_transfer_failed_physical():
    x=m.build(ROOT)
    assert x['element_evidence']['q_pipeline_exact_verdict']=='PASS'
    assert x['element_evidence']['retained_D_r2_SS_setup_ns'] < 0
    assert x['element_evidence']['selected_q_pipeline_option'] is None


def binding():
    return dict(write_clock_GHz=.9, field_clock_GHz=1.2, reverse_capture_clock_GHz=.9,
        gear_bound_ns=4,bank_service_II_edges=6,route_service_II_edges=1,
        packet_route_edges=16, checked_old_stripe_read_edges=1,decode_old_edges=1,
        merge_encode_edges=1,data_check_commit_edges=1,checked_publication_edges=1,
        registered_receipt_edges=1,reverse_CDC_edges=2,forward_CDC_edges=2,
        bank_pipeline_capacity_rows=1,bank_service_rows_ahead_bound=5,
        RMW_ports_reserved=True,all_six_copy_visible_receipt=True,
        old_head_identity_match=True,reverse_count_identity_match=True)


def test_bank_II_includes_inflight_and_receiver_clock():
    b=binding();x=m.vm_service(b)
    assert x['queued_and_inflight_predecessor_wait_edges']==30
    assert x['bank_port_occupation_edges']==6
    assert x['bound_ns']==pytest.approx(4+(30+22)/.9+2/.9)
    faster=copy.deepcopy(b);faster['reverse_capture_clock_GHz']=1.2
    assert m.vm_service(faster)['bound_ns'] < x['bound_ns']


def test_low_II_without_pipeline_capacity_rejected():
    b=binding();b['bank_service_II_edges']=1
    with pytest.raises(ValueError,match='capacity'):m.vm_service(b)
    b['bank_pipeline_capacity_rows']=6
    assert m.vm_service(b)['bound_ns'] > 0


@pytest.mark.parametrize('field',['write_clock_GHz','merge_encode_edges','reverse_capture_clock_GHz'])
def test_missing_positive_measurement_never_zero(field):
    b=binding();b[field]=None
    assert m.vm_service(b)['bound_ns'] is None
    b[field]=0
    with pytest.raises(ValueError):m.vm_service(b)


def test_parallel_ranks_join_max_and_shared_port_serialization():
    events=[dict(id='r0',deps=[],duration_ns=10),dict(id='r1',deps=[],duration_ns=12),
            dict(id='bank2',deps=['r0'],duration_ns=4),
            dict(id='sink',deps=['bank2','r1'],duration_ns=2)]
    assert m.solve_events(events)['finish_ns']['sink']==16
    events[1]['deps']=['r0']
    assert m.solve_events(events)['finish_ns']['sink']==24


def test_unknown_cost_taints_consumer_and_no_out_of_order_input():
    events=[dict(id='read',deps=[],duration_ns=None),dict(id='sink',deps=['read'],duration_ns=2)]
    assert m.solve_events(events)['finish_ns']['sink'] is None
    assert m.solve_events(events)['unbound_events']['sink']==['read']
    with pytest.raises(ValueError):m.solve_events(list(reversed(events)))


def test_existing_functions_AST_unchanged():
    # Base is immutable branch source; no other calculation is altered.
    base=subprocess.check_output(['git','show','4de034ca442410e8fc850f851cb0a3c97f6a6b4e:tools/uarch_model.py'],cwd=ROOT,text=True)
    before={n.name:ast.dump(n) for n in ast.parse(base).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    snapshot=subprocess.check_output(['git','show','386cd8beb526400aef55055c351f03dd703c2459:tools/uarch_model.py'],cwd=ROOT,text=True)
    after={n.name:ast.dump(n) for n in ast.parse(snapshot).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert set(after)-set(before)=={'dsrom_s81_minimum_group'}
    old_other = [ast.dump(n) for n in ast.parse(base).body if not isinstance(n, ast.FunctionDef)]
    new_other = [ast.dump(n) for n in ast.parse(snapshot).body if not isinstance(n, ast.FunctionDef)]
    assert old_other == new_other
    current={n.name:ast.dump(n) for n in ast.parse((ROOT/'tools/uarch_model.py').read_text()).body if isinstance(n, ast.FunctionDef)}
    assert current['dsrom_s81_minimum_group']==after['dsrom_s81_minimum_group']
    for k in before:
        if k!='main':assert before[k]==after[k],k


def test_committed_model_byte_replay():
    out=json.dumps(m.build(ROOT),indent=2,sort_keys=True,allow_nan=False)+'\n'
    assert out==(ROOT/m.NS/'model.json').read_text()
