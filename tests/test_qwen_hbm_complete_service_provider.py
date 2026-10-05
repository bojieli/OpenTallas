"""Synthetic supplied callback timelines test protocol, not provider timing."""
from fractions import Fraction
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_service_provider import CallbackProvider, FAST, SLOW, crossing, model

def edge(value, period):
    return ((Fraction(value)+period-1)//period)*period if period.denominator == 1 else (Fraction(value)//period+1)*period

def prerequisites(provider, position, instruction, now):
    if (position, instruction) in provider.retired:
        return
    for dependency in provider.graph['instructions'][instruction]['dependencies']:
        prerequisites(provider, position, dependency, now)
    provider.retire(position, instruction, now, now)

def started():
    provider = CallbackProvider(); writer = next(iter(provider.links))
    for dependency in provider.graph['instructions'][writer]['dependencies']:
        prerequisites(provider, 0, dependency, 0)
    provider.begin(0, writer, 42, 35, 0)
    return provider, (0, writer)

def sector(provider, key, ordinal, tag, start):
    transaction = provider.reserve_sector(key, ordinal, tag, start)
    descriptor = provider.slots[transaction]['descriptor']
    issue = edge(crossing(start, FAST), FAST)
    if descriptor['partial']:
        provider.command(transaction, 'read', issue)
        returned = issue+10000
        merged = edge(crossing(returned, SLOW), SLOW)+27*SLOW
        provider.RMW_return_merge(transaction, returned, merged)
        issue = edge(merged+FAST, FAST)
    provider.command(transaction, 'write', issue)
    visible = issue+7274
    provider.WR_visible(transaction, issue, visible)
    accepted = crossing((visible//FAST+1)*FAST, SLOW)
    stored = edge(accepted, SLOW); retired = stored+SLOW
    provider.sector_consumer(transaction, 42, accepted, stored, retired)
    released = crossing(retired, FAST)
    provider.release_sector(transaction, released)
    return released

def test_model_actual_fullshape_writers_stack_skew_and_priced_scoreboard():
    result = model()
    assert result['encoded_program_instructions'] == 1737
    assert len(result['bindings']) == 72 and len(result['writer_demands']) == 144
    assert {tuple(r['commands_by_stack']) for r in result['writer_demands']} == {
        (128,128,144,128), (128,128,128,144)}
    assert all(r['busiest_stack_command_floor']==144 for r in result['writer_demands'])
    assert result['additional_storage']['scoreboard_bits'] == 1137*2
    assert not result['engine_RTL_build_ready'] and result['full_token_cycles'] is None

def test_supplied_272_sector_callbacks_publish_without_holding_all_sector_credits():
    provider, key = started()
    for ordinal in range(272):
        final = sector(provider, key, ordinal, ordinal, ordinal*100000)
    assert not provider.slots and not provider.locks
    assert len(provider.writers[key]['completed']) == 272
    provider.publish(key, 42, final)
    # Regression: absence of a lease is not proof that the mandatory reader
    # has completed. Previously this release stranded the encoded KV_READ.
    with pytest.raises(ValueError, match='mandatory encoded KV_READ lease'):
        provider.release_writer_context(key)
    assert not provider.writers[key]['released']
    writer = key[1]; link = provider.links[writer]
    provider.retire(0, writer, final, final)
    provider.retire(0, link['fence'], final, final)
    provider.acquire_read(key, 42, final)
    provider.retire(0, link['read'], final, final)
    prerequisites(provider, 0, link['scores'], final)
    with pytest.raises(ValueError, match='SCORES/PV'):
        provider.release_read(key, final)
    with pytest.raises(ValueError, match='live reader'):
        provider.release_writer_context(key)
    prerequisites(provider, 0, link['pv'], final)
    provider.release_read(key, final)
    provider.release_writer_context(key)
    assert not provider.leases

def test_published_writer_context_cannot_release_before_mandatory_read():
    provider, key = started()
    for ordinal in range(272):
        final = sector(provider, key, ordinal, ordinal, ordinal*100000)
    provider.publish(key, 42, final)
    with pytest.raises(ValueError, match='mandatory encoded KV_READ lease'):
        provider.release_writer_context(key)
    assert not provider.writers[key]['released']
    writer = key[1]; link = provider.links[writer]
    provider.retire(0, writer, final, final)
    provider.retire(0, link['fence'], final, final)
    provider.acquire_read(key, 42, final)
    provider.retire(0, link['read'], final, final)
    assert key in provider.leases
    with pytest.raises(ValueError, match='live reader'):
        provider.release_writer_context(key)

def test_four_sector_credits_and_sector_lock_are_finite():
    provider, key = started()
    for ordinal in range(4):
        provider.reserve_sector(key, ordinal, ordinal, 0)
    with pytest.raises(ValueError, match='credit unavailable'):
        provider.reserve_sector(key, 4, 4, 0)

def test_one_live_writer_per_die_and_36_client_aperture_are_finite():
    provider, key = started()
    other = next(r['writer'] for r in provider.links.values() if r['die']==0 and r['writer'] != key[1])
    with pytest.raises(ValueError, match='contexts exhausted'):
        provider.begin(0, other, 42, 0, 0)
    with pytest.raises(ValueError, match='36-client aperture'):
        provider.begin(0, other, 42, 36, 0)

def test_actual_WR_visible_and_reverse_CDC_are_required_before_sector_retire():
    provider, key = started()
    tag = provider.reserve_sector(key, 0, 0, 0)
    issue = edge(crossing(0, FAST), FAST)
    provider.command(tag, 'read', issue)
    returned = issue+10000; merged = edge(crossing(returned,SLOW),SLOW)+27*SLOW
    provider.RMW_return_merge(tag, returned, merged)
    issue = edge(merged+FAST,FAST); provider.command(tag,'write',issue)
    with pytest.raises(ValueError,match='backing visibility'):
        provider.WR_visible(tag,issue,issue)
    visible = issue+7274; provider.WR_visible(tag,issue,visible)
    with pytest.raises(ValueError,match='landing is not'):
        provider.sector_consumer(tag,42,visible,visible,visible)
    accepted = crossing((visible//FAST+1)*FAST,SLOW)
    stored = edge(accepted,SLOW); retired=stored+SLOW
    provider.sector_consumer(tag,42,accepted,stored,retired)
    with pytest.raises(ValueError,match='reverse CDC'):
        provider.release_sector(tag,retired)

def test_incomplete_publication_and_stale_generation_fail():
    provider, key = started()
    sector(provider, key, 0, 0, 0)
    with pytest.raises(ValueError, match='incomplete/stale'):
        provider.publish(key, 42, 100000)
    with pytest.raises(ValueError, match='unpublished'):
        provider.acquire_read(key, 42, 100000)
    with pytest.raises(ValueError, match='stale'):
        provider.acquire_read(key, 43, 100000)

def test_RMW_requires_return_merge_and_one_shared_command_per_stack_cycle():
    provider, key = started()
    tag = provider.reserve_sector(key, 0, 0, 0)
    issue = edge(crossing(0, FAST), FAST)
    with pytest.raises(ValueError, match='actual RMW merge'):
        provider.command(tag, 'write', issue)
    provider.command(tag, 'read', issue)
    other = provider.reserve_sector(key, 1, 1, 0)
    with pytest.raises(ValueError, match='one shared'):
        provider.command(other, 'read', issue)

def test_acceptance_cannot_release_credit_and_late_result_cannot_retire():
    provider, key = started()
    tag = provider.reserve_sector(key, 0, 0, 0)
    with pytest.raises(ValueError, match='actual consumer retire'):
        provider.release_sector(tag, 100000)
    with pytest.raises(ValueError, match='unwritten sector ACK'):
        provider.sector_consumer(tag, 42, 10000, 20000, 30000)
    with pytest.raises(ValueError, match='before result visibility'):
        provider.retire(0, 0, 1000, 0)

def test_second_token_requires_published_previous_generation_not_only_current():
    provider = CallbackProvider(); writer = next(iter(provider.links))
    for dependency in provider.graph['instructions'][writer]['dependencies']:
        prerequisites(provider, 1, dependency, 0)
    provider.begin(1, writer, 42, 35, 0)
    for ordinal in range(272):
        final = sector(provider, (1,writer), ordinal, ordinal, ordinal*100000)
    with pytest.raises(ValueError, match='cannot skip previous generation'):
        provider.publish((1,writer), 42, final)
    with pytest.raises(ValueError, match='previous/current generation unpublished'):
        provider.acquire_read((1,writer), 42, final)
