#!/usr/bin/env python3
"""Offline proof of fixed-cycle SU frame reuse and emitted drain masks.

JSON input has allocations, writes and drains lists. Allocation: id, owner,
frame (0..3), generation, begin, end (exclusive). Every event repeats allocation,
owner, frame and generation: physical frame equality alone is insufficient.
Events declare issue_edge, latency and capture_edge == issue_edge + latency.
Writes additionally have kind (stage/compute), sector and mask (8 bits).
Drain masks describe the words whose last committed writer is compute in this
allocation. A read at edge k sees writes committed strictly before k; its data
returns at capture_edge. No readiness, credit or runtime epoch is modelled.
This checker proves supplied calendars, not that an actual program emits them.
"""
import argparse
import json


class CalendarError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise CalendarError(message)


def integer(record, key, low=0):
    value = record[key]
    require(type(value) is int and value >= low, f'invalid integer {key}')
    return value


def validate(calendar):
    require(calendar['N'] == 512 and calendar['M'] == 128,
            'production shape must be N512/M128')
    allocations = {}
    frames = [[] for _ in range(4)]
    for a in calendar['allocations']:
        require(isinstance(a['id'], str) and a['id'] and a['id'] not in allocations,
                'duplicate or invalid allocation identity')
        require(isinstance(a['owner'], str) and a['owner'], 'invalid owner')
        f = integer(a, 'frame')
        require(f < 4, 'frame outside four-frame store')
        integer(a, 'generation')
        require(set(a['sources']) == {'stage', 'compute'} and
                all(isinstance(s, str) and s for s in a['sources'].values()),
                'invalid source identities')
        require(integer(a, 'end') > integer(a, 'begin'), 'empty ownership interval')
        allocations[a['id']] = a
        frames[f].append(a)
    require(allocations, 'empty calendar')
    reuse = 0
    for sequence in frames:
        sequence.sort(key=lambda a: a['begin'])
        for old, new in zip(sequence, sequence[1:]):
            require(old['end'] <= new['begin'], 'overlapping frame ownership')
            require(old['generation'] < new['generation'], 'generation not increasing')
            reuse += 1

    def event(e):
        require(e['allocation'] in allocations, 'unknown allocation')
        a = allocations[e['allocation']]
        for field in ('owner', 'frame', 'generation'):
            require(e[field] == a[field], f'{field} identity mismatch')
        issue = integer(e, 'issue_edge')
        capture = integer(e, 'capture_edge')
        latency = integer(e, 'latency')
        require(capture == issue + latency, 'declared latency/capture mismatch')
        require(a['begin'] <= issue <= capture < a['end'],
                'event capture outside ownership: stale writer or late return')
        require(integer(e, 'sector') < 8192, 'sector outside 65536-word frame')
        require(integer(e, 'mask') < 256, 'mask outside sector')
        return a

    timelines = {key: [] for key in allocations}
    for w in calendar['writes']:
        a = event(w)
        require(w['kind'] in ('stage', 'compute'), 'unknown write kind')
        require(w['source'] == a['sources'][w['kind']], 'write source identity mismatch')
        timelines[a['id']].append(w)
    # One ordered history per sector word. Colliding writes are rejected; no
    # behavioral last-port priority is silently assumed by the compiler proof.
    histories = {}
    write_words = 0
    for aid, writes in timelines.items():
        for w in sorted(writes, key=lambda w: w['capture_edge']):
            for bit in range(8):
                if w['mask'] & (1 << bit):
                    key = (aid, w['sector'], bit)
                    history = histories.setdefault(key, [])
                    require(not history or history[-1][0] != w['capture_edge'],
                            'same-edge write collision')
                    history.append((w['capture_edge'], w['kind']))
                    write_words += 1
    checked_words = 0
    for d in calendar['drains']:
        a = event(d)
        require(d['source'] == a['sources']['compute'], 'drain source identity mismatch')
        expected = 0
        for bit in range(8):
            latest = None
            for edge, kind in histories.get((a['id'], d['sector'], bit), []):
                if edge >= d['issue_edge']:
                    break
                latest = kind
            if latest == 'compute':
                expected |= 1 << bit
            checked_words += 1
        require(d['mask'] == expected,
                f"drain mask mismatch allocation={a['id']} sector={d['sector']} "
                f"edge={d['issue_edge']} expected={expected} emitted={d['mask']}")
    return dict(status='PASS', allocations=len(allocations), frame_reuses=reuse,
                frames_used=sum(bool(s) for s in frames),
                write_events=len(calendar['writes']), write_words=write_words,
                drain_events=len(calendar['drains']), checked_mask_bits=checked_words,
                qualification='supplied fixed-cycle calendar proof only; no actual program/native/throughput qualification')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('calendar')
    args = parser.parse_args()
    with open(args.calendar) as stream:
        print(json.dumps(validate(json.load(stream)), indent=2))


if __name__ == '__main__':
    main()
