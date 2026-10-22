#!/usr/bin/env python3
"""Audit observed CAP tag domains and legal descriptor-change windows.

This is an observational contract audit, never a numerical qualification.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


def audit(path):
    raw = Path(path).read_bytes()
    text = gzip.decompress(raw).decode() if str(path).endswith('.gz') else raw.decode()
    pattern = re.compile(r'CAP_LIFETIME t=(\d+) fa=([01])/([0-9a-f]+) fb=([01])/([0-9a-f]+) open=([01])')
    events = []
    idle_times = []
    for match in pattern.finditer(text):
        t, av, at, bv, bt, opened = match.groups()
        if opened == '0':
            idle_times.append(int(t))
        for port, valid, tag in [('A', av, at), ('B', bv, bt)]:
            tag = int(tag, 16)
            if valid == '1' and ((tag >> 8) & 31) == 0 and (1 << ((tag >> 5) & 7)) >= (tag & 31):
                row = (tag >> 13) & 65535
                events.append(dict(t=int(t), port=port, row=row, row_flags=row >> 14, pos=tag >> 29, open=int(opened)))
    domains = {}
    for event in events:
        domains.setdefault(event['row_flags'], []).append(event)
    transitions = []
    for a, b in zip(events, events[1:]):
        if a['row_flags'] != b['row_flags']:
            idle = [t for t in idle_times if a['t']+4 <= t < b['t']-4]
            transitions.append(dict(before=a, after=b, row_span=abs(a['row']-b['row'])+1,
                                    observed_idle_cfg_candidate_edges=idle))
    return dict(scope='OBSERVATIONAL_ONLY; no CAP/CW/VP numerical PASS', input_sha256=hashlib.sha256(raw).hexdigest(),
                complete_words_at_FIN=len(events),
                domains={str(flag): dict(count=len(es), row_min=min(e['row'] for e in es), row_max=max(e['row'] for e in es),
                                         first_t=es[0]['t'], last_t=es[-1]['t']) for flag, es in domains.items()},
                descriptor_rcnt_max=2047,
                descriptor_shared_range_possible=bool(events) and max(e['row'] for e in events)-min(e['row'] for e in events)<2047,
                transitions=transitions,
                cfg_count=text.count('ACTUAL_CAP_CFG '), cw_count=text.count('ACTUAL_CW '),
                terminal_lines=[line for line in text.splitlines() if 'FULLSIX_SOURCE_CHECK' in line or 'FULLSIX_PREPARATORY_TRACE_END' in line])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('log')
    p.add_argument('out')
    args = p.parse_args()
    result = audit(args.log)
    Path(args.out).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'transitions'}, indent=2))
    print('domain_transitions', len(result['transitions']))
