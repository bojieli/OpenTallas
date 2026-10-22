#!/usr/bin/env python3
"""Add explicit target3 CAP descriptors to a private source programme.

Candidate timing only: actual CFG/F11/CW/VP observations must qualify it.
"""
import argparse
import json
from pathlib import Path


def cap_word(flags):
    return (2 << 27) | (((flags << 14) + 6144) << 29) | (828 << 45)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('audit')
    parser.add_argument('output')
    args = parser.parse_args()
    commands = {int(line.split()[0]): int(line.split()[1], 16)
                for line in Path(args.source).read_text().splitlines()}
    audit = json.loads(Path(args.audit).read_text())
    phases = [(1700, 1)]
    phases.extend((t['after']['t']-9, t['after']['row_flags']) for t in audit['transitions'])
    records = []
    for edge, flags in phases:
        if edge in commands:
            raise ValueError(f'XR control collision at {edge}')
        body = cap_word(flags)
        commands[edge] = (body << 26) | (3 << 16) | (1 << 6)
        records.append(dict(xr_ctl_pin_edge=edge, flags=flags, cap_body=f'{body:040x}'))
    Path(args.output).write_text(''.join(f'{t} {v:047x}\n' for t,v in sorted(commands.items())))
    Path(args.output+'.cap.json').write_text(json.dumps(dict(scope='CANDIDATE NOT QUALIFIED', descriptors=records),indent=2)+'\n')
