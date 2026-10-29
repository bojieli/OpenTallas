#!/usr/bin/env python3
"""Reserve recurring HEAD slots from a static MU prepare/HOST timeline.

All dates use one selected programme's core-edge origin.  The result is a
source schedule candidate, never physical or token qualification.  Unlike a
filler age, this includes the user-zero HOST join and filler output priority.
"""
import argparse
import json
from pathlib import Path

from head_prepare_bound import host_core_interval, host_join


def edge(value, name):
    if type(value) is not int or value < 0:
        raise ValueError('explicit nonnegative core edge required: ' + name)
    return value


def reserve(component, timeline, compute_gen_sha256):
    if (timeline.get('schema') != 'opentallas.qwen.head_prepare_timeline.v1' or
            timeline.get('compute_gen_sha256') != compute_gen_sha256 or
            not isinstance(compute_gen_sha256, str) or len(compute_gen_sha256) != 64):
        raise ValueError('selected compute GEN timeline required')
    if component.get('schema') != 'opentallas.qwen.bound_head_prepare_age.v1':
        raise ValueError('actual bound HEAD component required')
    delays = component['edges']
    for name in ('tt_local', 'tt_to_native', 'native_prepare_descriptor',
                 'native_to_face', 'face_input', 'face_held_bank'):
        edge(delays[name], name)
    if delays['native_prepare_descriptor'] != 3 or delays['face_held_bank'] != 1:
        raise ValueError('unsupported actual prepare/held-bank implementation')
    outgoing = timeline['outgoing']
    # A calendar callback can precede its eventual bank sample. Preserve that
    # endpoint explicitly instead of treating a published output-wire date as
    # a calendar slot or prematurely releasing an occupied held bank.
    bank_offset = outgoing['send_slot_to_bank_sample_edges']
    if type(bank_offset) is not int:
        raise ValueError('explicit signed slot-to-bank sample offset required')
    record_offset = edge(outgoing['send_slot_to_record_capture_edges'], 'send_slot_to_record_capture_edges')
    if record_offset < bank_offset:
        raise ValueError('record capture precedes its actual source bank sample')
    if not outgoing.get('path'):
        raise ValueError('actual held-bank to outgoing calendar path required')
    events = timeline['events']
    if not events or {e['user'] for e in events} != {0, 1, 2, 3}:
        raise ValueError('all four MU owners require actual prepare reservations')
    rows = []
    sampled = set()
    for event in events:
        sample = edge(event['calendar_sample_edge'], 'calendar_sample_edge')
        origin = edge(event['run_start_edge'], 'run_start_edge')
        user = event['user']
        if type(user) is not int or not 0 <= user < 4:
            raise ValueError('invalid actual MU owner')
        if type(event['token']) is not int or not 0 <= event['token'] < 151936:
            raise ValueError('invalid prepare token')
        if type(event['position']) is not int or not 0 <= event['position'] < 8192:
            raise ValueError('invalid prepare position')
        publication = sample + delays['tt_local'] + delays['tt_to_native']
        # Transport ages end at a post-edge published input.  The native
        # pipeline samples that tuple on the following edge. host_join uses
        # this pre-edge sampling basis, unlike the source-local age ledger.
        capture = publication + 1
        if capture in sampled:
            raise ValueError('two prepares collide on the sole native input')
        sampled.add(capture)
        rows.append(dict(event, native_prepare_publication_edge=publication,
                         native_prepare_capture_edge=capture,
                         descriptor_core_edge=publication + delays['native_prepare_descriptor']))
    busy = [r['descriptor_core_edge'] for r in rows if r['user']]
    for row in rows:
        if row['user'] == 0:
            host = host_core_interval(row['host_at_sysface'], component)
            joined = host_join(row['native_prepare_capture_edge'], row['token'],
                               row['position'], host, busy)
            row['descriptor_core_edge'] = joined['descriptor_core_edge']
            row['host_at_native'] = host
        row['held_bank_ready_edge'] = row['descriptor_core_edge'] + sum(
            delays[k] for k in ('native_to_face', 'face_input', 'face_held_bank'))
        row['earliest_send_slot_edge'] = row['held_bank_ready_edge'] + 1 - bank_offset
    # A single recurring slot serves every user; dates are converted from the
    # shared absolute programme origin to each owner's actual token-run origin.
    slot = max(5, max(r['earliest_send_slot_edge'] - r['run_start_edge'] for r in rows))
    forbidden = {edge(x, 'forbidden_send_slot') for x in timeline['forbidden_send_slots']}
    while slot in forbidden:
        slot += 1
    for row in rows:
        row['reserved_send_slot_edge'] = row['run_start_edge'] + slot
        row['reserved_bank_sample_edge'] = row['reserved_send_slot_edge'] + bank_offset
        row['reserved_record_capture_edge'] = row['reserved_send_slot_edge'] + record_offset
        if row['reserved_send_slot_edge'] > edge(row['latest_send_slot_edge'], 'latest_send_slot_edge'):
            raise ValueError('HEAD reservation misses outgoing descriptor deadline')
    if len({r['reserved_send_slot_edge'] for r in rows}) != len(rows):
        raise ValueError('two owners collide on the sole outgoing HEAD port')
    # One outstanding user0 pending prepare, and one held bank per owner.
    # A source timeline that overwrites either state is not fixed by a later slot.
    for user in range(4):
        owner_rows = sorted((r for r in rows if r['user'] == user), key=lambda r:r['native_prepare_capture_edge'])
        for previous, current in zip(owner_rows, owner_rows[1:]):
            if user == 0 and current['native_prepare_capture_edge'] + 2 <= previous['descriptor_core_edge']:
                raise ValueError('next user0 prepare overwrites pending HOST join')
            if current['held_bank_ready_edge'] <= previous['reserved_bank_sample_edge']:
                raise ValueError('next descriptor overwrites an occupied owner held bank')
    return dict(schema='opentallas.qwen.head_prepare_reservation.v1',
                status='SOURCE_SCHEDULE_CANDIDATE', compute_gen_sha256=compute_gen_sha256,
                head_prepare_edges=slot, outgoing=outgoing, reservations=rows,
                runtime_waiting=False, physical_qualified=False, token_qualified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('bound-component', 'timeline', 'compute-gen-sha256', 'out'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    try:
        result = reserve(json.loads(Path(a.bound_component).read_text()),
                         json.loads(Path(a.timeline).read_text()), a.compute_gen_sha256)
        code = 0
    except (KeyError, ValueError, OSError) as e:
        result = dict(status='BLOCKED', reason=str(e)); code = 2
    Path(a.out).write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])
    return code


if __name__ == '__main__':
    raise SystemExit(main())
