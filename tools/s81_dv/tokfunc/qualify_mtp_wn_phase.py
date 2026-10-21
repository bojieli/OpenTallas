#!/usr/bin/env python3
"""Seal the terminal phase-congruent WN component receipt; never a token PASS."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def qualify(directory, run_exit, unit):
    if run_exit != 0:
        raise ValueError('Actual fleet runner must have reported terminal exit zero')
    root = Path(directory)
    rec = json.loads((root / 'phase_receipt.json').read_text())
    if rec.get('result') != 'PASS' or rec.get('errors'):
        raise ValueError('The actual graph-deadline replay has not passed')
    messages = rec['messages']
    quantum = rec['phase_quantum']
    offset = rec['graph_to_bench_offset']
    if quantum != 4 or rec['phase_preserved'] is not True or offset % quantum:
        raise ValueError('Graph phase was not preserved')
    if len(messages) != 12 or rec['positions'] != 6 or rec['beats'] != 3840:
        raise ValueError('Incomplete current six-position component inventory')
    expected = {m['inst']: m for m in messages}
    counts = dict.fromkeys(expected, 0)
    text = (root / 'run.log').read_text()
    stats = re.findall(
        r'^WN_STATS beats (\d+) landed (\d+) mismatch (\d+) extra (\d+) late (\d+) '
        r'tags (\d+)/(\d+) tagbad (\d+) fault ([01]+) live ([01]+) '
        r'minage (\d+) maxage (\d+) last_cycle (\d+)$', text, re.M)
    if len(stats) != 1:
        raise ValueError('Missing or ambiguous actual terminal statistics')
    s = stats[0]
    if tuple(map(int, s[:8])) != (3840, 3840, 0, 0, 0, 3840, 3840, 0) or s[8:10] != ('0', '1111'):
        raise ValueError('Actual data, tag, fault or live checks failed')
    if 'PASS mtp_wn_positions:' not in text:
        raise ValueError('Actual engine has no terminal PASS')
    if hashlib.sha256((root / 'run.log').read_bytes()).hexdigest() != rec['run_log_sha256']:
        raise ValueError('Raw log differs from the terminal receipt')
    for line in text.splitlines():
        match = re.fullmatch(r'WN_LAND (\d+) (\d+) (\d+) (\d+) (\d+)', line)
        if not match:
            continue
        inst, _, issue, land, deadline = map(int, match.groups())
        m = expected[inst]
        if deadline != m['complete_deadline'] or deadline == 0 or land > deadline:
            raise ValueError('Actual absolute bench-cycle deadline failed or is unqualified')
        if issue < m['issue'] or land < m['first_allowed']:
            raise ValueError('Actual issue/landing precedes the graph reservation')
        if m['issue'] - m['graph_send'] != offset:
            raise ValueError('Message clock mapping differs from the certified constant offset')
        counts[inst] += 1
    if set(counts.values()) != {320}:
        raise ValueError('Actual messages do not each contain all 320 beats')
    first = messages[0]
    rec.update(
        run=dict(exit=run_exit, unit=unit),
        phase_congruence=dict(quantum=quantum, graph_first_send=first['graph_send'],
                              bench_first_issue=first['issue'], offset=offset, preserved=True),
        absolute_deadlines_checked=True, first_landing_lower_bounds_checked=True,
        deadline_clock_basis='absolute bench cycle = graph cycle + recorded phase-congruent constant offset',
        positions_executed=6, clock_cycles_executed=int(s[-1]),
        current_token_provenance_qualified=False,
        qualification_scope='one source-pinned WN rank transport component; deterministic diagnostic payloads/tags; '
                            'not whole stage/barrier/token or real HOST/PW/KS descriptor provenance')
    return rec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--run-exit', required=True, type=int)
    parser.add_argument('--unit', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    rec = qualify(args.run, args.run_exit, args.unit)
    Path(args.out).write_text(json.dumps(rec, indent=2) + '\n')
    print('PASS_SOURCE_COMPONENT; full token remains INCOMPLETE')


if __name__ == '__main__':
    main()
