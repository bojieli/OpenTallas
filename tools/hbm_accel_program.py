#!/usr/bin/env python3
"""Default-off, W19-compatible HA5 scheduling; no arithmetic or ISA changes.

The returned ops run through the existing Executor, including split_ea at the
existing expert_intermediate_gather. Hardware overlap remains an unvalidated
hypothesis. Selector assignments are an implementation plan, not new opcodes.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def shared_prefix(op):
    return ((op.get('kind') == 'mv' and op.get('w') in
             ([6, 'w1'], [6, 'w3'], (6, 'w1'), (6, 'w3')))
            or (op.get('fn') == 'swiglu' and op.get('slot') == 6))


def schedule_ops(ops, shared_first=False):
    result = copy.deepcopy(ops)
    if not shared_first:
        return result
    fetches = [o for o in result if o['kind'] == 'expert_fetch']
    if not fetches:  # head
        return result
    if len(fetches) != 1 or fetches[0]['experts'] != 6:
        raise ValueError('HA5 requires one six-expert W19 fetch')
    prefix = [o for o in result if shared_prefix(o)]
    if len(prefix) != 3 or [o.get('w') for o in prefix[:2]] != [[6, 'w1'], [6, 'w3']]:
        # JSON inputs carry lists; in-memory Compiler outputs carry tuples.
        if len(prefix) != 3 or [o.get('w') for o in prefix[:2]] != [(6, 'w1'), (6, 'w3')]:
            raise ValueError('missing canonical shared w1/w3/SwiGLU chain')
    fetch = result.index(fetches[0])
    gather = next(i for i, o in enumerate(result) if o.get('tag') == 'expert_intermediate_gather')
    if not all(fetch < result.index(o) < gather for o in prefix):
        raise ValueError('shared prefix outside canonical expert region')
    if result[fetch - 1].get('fn') != 'route':
        raise ValueError('route identity must be resolved before shared issue')
    result = [o for o in result if not shared_prefix(o)]
    fetch = next(i for i, o in enumerate(result) if o['kind'] == 'expert_fetch')
    # Request routed weights at the original point. Shared compute may issue
    # while those weights are outstanding; delaying this request would add an
    # extra SM drain/barrier and does not create an overlap window.
    result[fetch+1:fetch+1] = prefix
    # w2 consumes the same gathered intermediates, independent by slot. Keep
    # shared issue first here too, while the later moe_sum still adds 0..6.
    shared_down = [o for o in result if o.get('kind') == 'mv'
                   and o.get('w') in ([6, 'w2'], (6, 'w2'))]
    if len(shared_down) != 1:
        raise ValueError('missing shared w2')
    down = next(i for i, o in enumerate(result) if o.get('kind') == 'mv'
                and isinstance(o.get('w'), (list, tuple)) and o['w'][1] == 'w2')
    gathered = next(i for i,o in enumerate(result) if o.get('tag')=='expert_intermediate_gather')
    if down != gathered+1 or result.index(shared_down[0]) < down:
        raise ValueError('noncanonical expert down-projection region')
    result.remove(shared_down[0])
    result.insert(down, shared_down[0])
    for i, op in enumerate(result):
        op['id'] = i
    return result


def compile_program(program, shared_first=False):
    result = copy.deepcopy(program)
    for layer in result['layers']:
        layer['ops'] = schedule_ops(layer['ops'], shared_first)
    return result


def execute_layer(executor, ops, shared_first=False):
    """Run with the unchanged W19 executor and its original ea split boundary.

    This adapter does not instantiate a model or regenerate a golden. Actual
    model execution must use the owner's approved execution host and source.
    """
    scheduled = schedule_ops(ops, shared_first)
    gathers = [i for i,o in enumerate(scheduled)
               if o.get('tag') == 'expert_intermediate_gather']
    if not gathers:
        executor.run(scheduled)
    elif len(gathers) == 1:
        split = gathers[0]+1
        executor.run(scheduled[:split])
        executor.split_ea()
        executor.run(scheduled[split:])
    else:
        raise ValueError('ambiguous expert intermediate boundary')


def selector_plan(program, positions=1, replicas=1):
    if not 1 <= replicas <= positions <= 6:
        raise ValueError('require 1 <= replicas <= positions <= 6 (DSpark verify)')
    return [dict(layer=layer['layer'], op=op['id'], what=op['what'],
                 positions=[dict(position=p, replica=p % replicas, wave=p // replicas)
                            for p in range(positions)],
                 bytes_per_position=op['bytes'], reduction_order='unchanged per position')
            for layer in program['layers'] for op in layer['ops'] if op['kind'] == 'topk_merge']


def merge_audit(program):
    """Conservative transport-only merges: adjacent gathers to identical receivers.

    Intervening arithmetic may consume the first collective or produce the second;
    do not cross it or change any golden reduction tree/rounding point.
    """
    opportunities = []
    boundaries = []
    for layer in program['layers']:
        ops = layer['ops']
        cols = [(i, o) for i, o in enumerate(ops) if o['unit'] == 'COLL']
        for (i, a), (j, b) in zip(cols, cols[1:]):
            safe = (j == i + 1 and a['kind'] == b['kind'] == 'all_gather'
                    and a.get('dest') == b.get('dest')
                    and not set(a['bufs']) & set(b['bufs']))
            row = dict(layer=layer['layer'], first=a['tag'], second=b['tag'],
                       intervening_ops=j-i-1, first_kind=a['kind'], second_kind=b['kind'],
                       transport_merge_candidate=safe,
                       reason=('same destination adjacent independent gathers' if safe else
                               'intervening dependency/producer' if j>i+1 else
                               'different transport/reduction semantics or overlapping buffers'))
            boundaries.append(row)
            if safe:
                opportunities.append(row)
    return dict(opportunities=opportunities, boundaries=boundaries,
                applied=0, removed_collectives=0,
                policy='no arithmetic reassociation; nonadjacent merges need a dependency proof')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--program', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--shared-first', action='store_true')
    ap.add_argument('--verify-positions', type=int, default=1)
    ap.add_argument('--selector-replicas', type=int, default=1)
    ap.add_argument('--plan-out', type=Path)
    a = ap.parse_args()
    prog = compile_program(json.loads(a.program.read_text()), a.shared_first)
    a.out.write_text(json.dumps(prog) + '\n')
    if a.plan_out:
        a.plan_out.write_text(json.dumps(dict(
            source_sha256=hashlib.sha256(a.program.read_bytes()).hexdigest(),
            shared_first=a.shared_first, adopted=False,
            selectors=selector_plan(prog, a.verify_positions, a.selector_replicas),
            merges=merge_audit(prog)), indent=2) + '\n')


if __name__ == '__main__':
    main()
