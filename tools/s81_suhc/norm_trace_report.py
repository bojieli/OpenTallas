#!/usr/bin/env python3
"""Report actual HC NORM event intervals; these are interface diagnostics, not native cost qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import re

EVENT = re.compile(r'NTRACE op=(\d+) event=(\w+) cyc=(\d+)')
JOB = re.compile(r'HCJ op=(\d+) kind=(\d+) start=(\d+) done=(\d+)')

def report(path):
    raw = path.read_text()
    events = {}
    for op, event, cycle in EVENT.findall(raw):
        events.setdefault(int(op), {}).setdefault(event, []).append(int(cycle))
    rows = []
    for op, kind, start, done in JOB.findall(raw):
        if int(kind) != 4:
            continue
        op, start, done = int(op), int(start), int(done)
        e = events.get(op, {})
        required = ('accept', 'sum_return', 'rsqrt_ready', 'return_row', 'writer_done')
        if any(not e.get(k) for k in required):
            raise ValueError(f'{path}: missing NORM event for op {op}: {e}')
        points = [e['accept'][0], e['sum_return'][0], e['rsqrt_ready'][0],
                  e['return_row'][0], e['return_row'][-1], e['writer_done'][0], done]
        if points != sorted(points):
            raise ValueError(f'{path}: unordered NORM events for op {op}: {points}')
        rows.append(dict(op=op, start=start, done=done, interface_cycles=done-start,
            accept_to_sum_return=points[1]-points[0], sum_return_to_rsqrt=points[2]-points[1],
            rsqrt_to_first_row=points[3]-points[2], first_to_last_row=points[4]-points[3],
            last_row_to_writer_done=points[5]-points[4], writer_done_to_interface_done=points[6]-points[5],
            raw_events=e))
    if not rows or 'HCG PASS' not in raw:
        raise ValueError(f'{path}: no successful NORM composition')
    return dict(log=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), jobs=rows)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', nargs='+', type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.write_text(json.dumps(dict(schema='opentallas.s81_hc_norm_trace.v1',
        qualification='DIAGNOSTIC_ONLY', endpoint='HC command acceptance to interface done; VM writes observed at request',
        runs=[report(x) for x in a.logs]), indent=2)+'\n')
