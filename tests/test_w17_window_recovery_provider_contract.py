import importlib.util
import sys
from pathlib import Path
from dataclasses import replace
import pytest
spec = importlib.util.spec_from_file_location('provider_contract', Path(__file__).parents[1] / 'tools/w17_window_recovery_provider_contract.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def receipts(actors=m.ACTORS):
    return [m.ModelReceipt(a,3,7) for a in actors]


def permit(s, **kw):
    return m.model_restart_predicate(s, receipts(), lease=3, revision=7,
                                    no_future_delivery=True, **kw)


def test_owner_zero_allows_other_clients_but_not_shared_reset():
    s = m.OwnerSnapshot(3, 7, other_client_entries=12)
    assert permit(s)
    assert not permit(s, shared_reset=True)
    assert not m.actual_admission()


@pytest.mark.parametrize('field', ['owner_reads','owner_writes','owner_queued',
 'owner_returns','owner_offer','owner_pipeline','latent_intents',
 'owner_ack_pending','invisible_writes'])
def test_each_owned_obligation_blocks(field):
    assert not permit(m.OwnerSnapshot(3,7,**{field:1}))


def test_freshness_freeze_publication_and_fence():
    s = m.OwnerSnapshot(3,7)
    for patch in ({'lease':2}, {'revision':6}, {'frozen':False},
                  {'publication_invalid':False}):
        assert not permit(replace(s,**patch))
    assert not m.model_restart_predicate(s, receipts(m.ACTORS-{'WRITE_VISIBLE'}),
          lease=3,revision=7,no_future_delivery=True)
    assert not m.model_restart_predicate(s,receipts(),lease=3,revision=7,
                                        no_future_delivery=False)


def test_actual_tag_owner_filter_exhaustive():
    assert sum(m.window_tag(t) for t in range(1<<17)) == 1<<14
    assert m.window_tag(1<<16)
    assert not m.window_tag(0)  # weight/B, not K
    assert not m.window_tag((1<<16)|(1<<14))  # CKV
    assert not m.window_tag((1<<16)|(2<<14))  # RoPE
    with pytest.raises(ValueError): m.window_tag(1<<17)


def test_fault_same_edge_accept_wins_over_cancel():
    for state in ('WC','WS'):
        assert m.fault_write_action(state,accepted_block=True,
            same_edge_grant=True,withdraw_receipt=True).startswith('drain')
        assert m.fault_write_action(state,accepted_block=True,
            withdraw_receipt=True).startswith('cancel_unaccepted')
        assert m.fault_write_action(state,accepted_block=True).startswith('retain')
    for state in ('WC_DONE','WS_DONE'):
        assert m.fault_write_action(state,accepted_block=True,
                                   withdraw_receipt=True).startswith('drain')


def test_invalid_intent_and_bounds():
    with pytest.raises(ValueError): m.fault_write_action('WS',accepted_block=False)
    with pytest.raises(ValueError): m.OwnerSnapshot(0,0,owner_reads=-1)
    with pytest.raises(ValueError): m.LivenessBounds(0,1,1,1,1)
    b = m.LivenessBounds(2,3,4,5,6)  # synthetic supplied assumptions
    assert b.conservative_cycles(8,32) == 399
    with pytest.raises(ValueError): b.conservative_cycles(9,32)
    assert m.timeout_action() == 'alarm_keep_frozen_preserve_all_owned_entries'


def test_provider_scope_complete_and_explicit_missing_contracts():
    assert set(m.PROVIDERS) == m.ACTORS
    for provider in m.PROVIDERS.values():
        assert provider['actual'] and provider['limitation'] and provider['required']
    assert 'DEFER' in m.NASH_HANDOFF['timer_decision']


def test_stale_duplicate_and_rejected_actor_receipts():
    s = m.OwnerSnapshot(3,7)
    rs = receipts()
    for bad in (replace(rs[0],lease=2),replace(rs[0],revision=6),
                replace(rs[0],empty=False),rs[1],rs[0].actor):
        altered = [bad] + rs[1:]
        assert not m.model_restart_predicate(s,altered,lease=3,revision=7,
                                            no_future_delivery=True)
    with pytest.raises(ValueError): m.ModelReceipt('PHY_FABRICATED',3,7)


def test_whole_domain_needs_separate_fence_and_all_other_tails_empty():
    s = m.OwnerSnapshot(3,7)
    assert not permit(s,shared_reset=True)
    assert permit(s,shared_reset=True,reset_domain_fence=True)
    for field in ('other_client_entries','other_invisible_writes',
                  'other_pending_delivery','other_latent_intents'):
        busy = replace(s,**{field:1})
        assert permit(busy)
        assert not permit(busy,shared_reset=True,reset_domain_fence=True)
