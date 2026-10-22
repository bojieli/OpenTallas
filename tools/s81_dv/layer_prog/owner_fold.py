#!/usr/bin/env python3
"""Encode the TP4 FP32 owner tree using three existing VS RB commands.

The caller must place the actual four producer rows in two adjacent row pairs.
This encoder does not create operand payloads or lower collective transport.
"""
import argparse
import json


def program(pair01, pair23, scratch, output, start=0, guard=8):
    addresses = [pair01, pair01 + 1, pair23, pair23 + 1,
                 scratch, scratch + 1, output]
    if any(not isinstance(a, int) or not 0 <= a < 1024 for a in addresses):
        raise ValueError('owner-fold row address outside 1024-row leaf store')
    if any(a % 2 for a in (pair01, pair23, scratch)):
        raise ValueError('owner-fold input and scratch pairs must be even aligned')
    if len(set(addresses)) != len(addresses):
        raise ValueError('owner-fold inputs, intermediates and output must not alias')
    if not isinstance(start, int) or not isinstance(guard, int) or start < 0 or guard < 0:
        raise ValueError('negative schedule edge or guard')
    # Existing VS_DUR RB law is n+19; the minimum replay checks n=1.
    # Guards reserve the command/leaf turnaround; no performance credit taken.
    duration = 20
    cmds = []
    for k, (source, dest, label) in enumerate([
        (pair01, scratch, 'p0+p1'),
        (pair23, scratch + 1, 'p2+p3'),
        (scratch, output, '(p0+p1)+(p2+p3)'),
    ]):
        word = 11 | source << 4 | 1 << 24 | dest << 32
        issue = start + k * (duration + guard)
        cmds.append(dict(op='RB', opcode=11, a0=source, ob=dest, n=1,
                         issue=issue, reserved_end=issue + duration,
                         word=f'{word:040x}', expression=label))
    return dict(schema='opentallas.s81.owner_fold.v1', commands=cmds,
        input_pairs=[pair01, pair23], intermediate_pair=scratch, output_row=output,
        end=cmds[-1]['reserved_end'],
        arithmetic='four FP32 lanes, existing ot_s81sl_vs RB / ot_dsrom_qadd, canonical TP4 pair tree',
        qualification='ENCODED: real producer-row placement, transport and RTL replay remain caller obligations')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('pair01', 'pair23', 'scratch', 'output'):
        p.add_argument('--' + key, type=int, required=True)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--guard', type=int, default=8)
    a = p.parse_args()
    print(json.dumps(program(**vars(a)), indent=2))


if __name__ == '__main__':
    main()
