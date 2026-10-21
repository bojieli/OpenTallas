#!/usr/bin/env python3
"""Encode the TP4 FP32 owner tree using three existing VS RB commands.

The caller must place the actual four producer rows in two adjacent row pairs.
This encoder does not create operand payloads or lower collective transport.
"""
import argparse
import json


def pair_vehicle(sid, leaf=0, layer='L0'):
    """Native, data-free recipe for eight FP32 outputs from four staged RD pairs.

    This is an unscheduled vehicle, not permission to launch it. Every stage pair
    must come from the corresponding real rank partial. A scheduler must bind
    each dependency to SRAM commit, not V ACK. Typed V cannot carry odd rows;
    all overlapping writes below use XRT's full-width local RD loopback.
    """
    if layer != 'L0':
        raise ValueError('896..917 vehicle lease is scoped to L0 only (Engram overlaps on other layers)')
    if not isinstance(sid, int) or not 0 <= sid < 16 or not isinstance(leaf, int) or not 0 <= leaf < 5:
        raise ValueError('invalid fold slice or leaf')
    from layer_prog.lower_vpx import send_cfg, _vp, _payload, K_RD

    stages = [896, 898, 900, 902]
    steps = []
    previous = [f'rank{r}.stage_pair_sram_commit' for r in range(4)]
    for half in range(2):
        copies = []
        for rank, dest in enumerate([904, 905, 908, 909]):
            ident = f'h{half}.copy{rank}'
            # Full-width local RD accepts odd destination rows. Its second
            # row is deliberately overwritten or discarded in reserved spill.
            cfg = send_cfg('E', K_RD, 0, 1 << sid, leaf, dest, 1)
            cfg = (cfg & ~15) | (1 << 44)  # dir=0, s_local=1
            steps.append(dict(id=ident, kind='LOCAL_RD_PAIR', source_row=stages[rank] + half,
                destination_rows=[dest, dest + 1], kept_row=dest,
                depends=previous if rank == 0 else [copies[-1] + '.sram_commit'],
                templates=[dict(target=4, word=f'{_payload(1 << sid, 4, 0, cfg):047x}'),
                           dict(target=0, word=f'{_payload(1 << sid, 0, 1 << leaf, _vp(6, a0=stages[rank] + half, n=1)):047x}')],
                requires=['config captured before lo; config and lo must not coincide',
                          'RDOUT input read and whole-pair destination SRAM commit completed']))
            copies.append(ident)
        p = program(904, 908, 912, 916 + half)
        for k, command in enumerate(p['commands']):
            ident = f'h{half}.rb{k}'
            steps.append(dict(id=ident, kind='VS_RB', source_pair=command['a0'],
                output_row=command['ob'], depends=[copies[-1] + '.sram_commit'] if k == 0 else [f'h{half}.rb{k-1}.sram_commit'],
                templates=[dict(target=0, word=f'{_payload(1 << sid, 0, 1 << leaf, int(command["word"], 16)):047x}')],
                requires=['previous VS command retired and source SRAM writes committed']))
        previous = [f'h{half}.rb2.sram_commit']
    return dict(schema='opentallas.s81.owner_fold.pair_vehicle.v1', admitted=False, layer=layer,
        row_lease=dict(slice_sid=sid, leaf=leaf, rows=[896, 917], qualified=False,
                       requires='check actual producer CAP and all L0 writer live ranges before scheduling'),
        staged_pairs=[dict(rank=r, rows=[a, a+1], producer='actual rank-local wo_b partial; unbound')
                      for r, a in enumerate(stages)],
        reserved_rows=list(range(896, 918)), operand_pairs=[904, 908],
        discarded_spill_rows=[906, 910], intermediate_pair=912, output_rows=[916, 917],
        arithmetic='FP32 ((p0+p1)+(p2+p3)), independently for both128b halves',
        commands=steps, lifetime_qualified=False,
        requires=['real wo_b capture to stage pairs, including rank identity and output indices',
                  'current full-width RD routes to this owner; no odd-row typed V',
                  'source-pinned fixed CTL/lo/commit/VS calendar and nonalias lifetimes',
                  'repeat per actual owned eight-element tile; consumer/result allgather binding'],
        qualification='ENCODED_UNSCHEDULED: no payload, issue dates, ACK extension or completion credit')


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
