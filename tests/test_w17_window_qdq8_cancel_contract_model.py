"""Finite contract and illegal-retirement controls; no RTL execution."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cancel', ROOT/'tools/w17_window_qdq8_cancel_contract_model.py')
m = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def filled(blocks=1):
    ledger = m.CancelLedger()
    for b in range(16):
        ledger.qe_terminal(b, consumer_ready=True)
    ledger.source_idle()
    for b in range(blocks):
        ledger.commit_block()
    return ledger


def test_all_finite_capture_and_write_cuts():
    assert len(m.bounded_contract_checks()) == 85


def test_sticky_fault_blocks_admission_but_drains_poison_suffix():
    ledger = m.CancelLedger()
    assert ledger.admission()
    assert not ledger.admission(simultaneous_fault=True)
    ledger.qe_terminal(0, poison=True)
    for b in range(1,16):
        assert not ledger.qe_terminal(b, consumer_ready=False)
    with pytest.raises(AssertionError):
        ledger.commit_block()
    assert not ledger.local_cancel_ack()  # terminal16 is not sourceidle
    ledger.source_idle()
    assert ledger.local_cancel_ack() and ledger.sticky_fault


def test_local_cancel_ack_never_cancels_wc_ws_credits():
    ledger = filled()
    ledger.grant_write(0)
    ledger.fault()
    assert ledger.local_cancel_ack() and not ledger.retired()
    assert ledger.issued == {0} and ledger.acked == set()
    with pytest.raises(AssertionError):
        ledger.request_fence()
    ledger.ack(0, consumer_ready=False)
    with pytest.raises(AssertionError):
        ledger.request_fence()  # missing scale obligation
    ledger.grant_write(1, consumer_ready=False)
    ledger.ack(1, consumer_ready=False)
    ledger.request_fence()
    assert not ledger.retired()
    with pytest.raises(AssertionError):
        ledger.complete_fence(context=ledger.context)  # ACK-as-visible mutant


def test_no_timer_transition_and_held_reversed_visibility():
    ledger = filled()
    ledger.fault()
    for i in range(2):
        ledger.grant_write(i)
        ledger.ack(i)
    ledger.request_fence()
    assert not ledger.retired()  # arbitrarily long time cannot retire
    ledger.provider_visible(1)
    assert not ledger.retired()
    ledger.provider_visible(0)
    assert not ledger.retired()  # missing delivery/owner fence
    ledger.complete_fence(context=ledger.context)
    assert ledger.retired()


@pytest.mark.parametrize('method', ['ack','provider_visible'])
def test_duplicate_stale_and_wrong_owner_controls(method):
    ledger = filled()
    ledger.grant_write(0)
    fn = getattr(ledger, method)
    with pytest.raises(AssertionError):
        fn(0, owner=0b101)
    with pytest.raises(AssertionError):
        fn(0, context=(0,0,1048575))
    fn(0)
    with pytest.raises(AssertionError):
        fn(0)


def test_read_eight_credits_fault_sink_no_consumer_ready():
    ledger = m.CancelLedger()
    tags = [(0b100<<14) | (9<<5) | sector for sector in range(8)]
    for pc,tag in enumerate(tags):
        ledger.accept_read(tag,pc)
    with pytest.raises(AssertionError):
        ledger.accept_read((0b100<<14)|(9<<5)|8,8)
    ledger.fault()
    with pytest.raises(AssertionError):
        ledger.read_reply(tags[0],1)
    with pytest.raises(AssertionError):
        ledger.read_reply(tags[0]+(1<<14),0)
    with pytest.raises(AssertionError):
        ledger.read_reply(tags[0]+32,0)
    for pc in reversed(range(8)):
        ledger.read_reply(tags[pc],pc,poison=(pc==7),consumer_ready=False)
    assert not ledger.reads and ledger.sticky_fault
    with pytest.raises(AssertionError):
        ledger.read_reply(tags[0],0)


def test_control_token_distinct_and_delivery_fence_required():
    ledger = m.CancelLedger(qe_accepted=False, control_token=1)
    ledger.fault();ledger.source_idle();ledger.request_fence()
    with pytest.raises(AssertionError):
        ledger.complete_fence(context=ledger.context,control_token=0)
    with pytest.raises(AssertionError):
        ledger.complete_fence(context=ledger.context,control_token=1,delivery=False)
    ledger.complete_fence(context=ledger.context,control_token=1)
    assert ledger.retired()


def test_pinned_sources_and_peirce_composed_model():
    record = m.generate()
    assert record['coordination']['adapter_commit'] == m.PEIRCE
    assert record['cost']['minimal_local_adapter_bits'] == 19
    assert record['cost']['optional_8credit_read_ledger_bits'] == 228
    assert record['healthy_landmarks']['producer_last_block_accept_cycle'] == 871
    assert record['healthy_landmarks']['final_WR_ack_cycle'] == 905
    assert record['healthy_landmarks']['declared_shadow_visible_ps'] == 911274
    assert not record['physical_WR_provider_qualified']
    assert not record['live_producer_safe'] and record['no_RTL'] and record['no_compile']
