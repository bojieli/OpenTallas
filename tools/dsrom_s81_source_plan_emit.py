#!/usr/bin/env python3
"""Emit the real caller factory from existing dispatch and owner TP4 order.

No map reload, operation compilation, input generation or model build. The
enclosing owner supplies its selected offer indices in actual schedule order;
rank-at-a-time dispatch and inferred grouping are deliberately not used.
"""
import argparse
import json
from pathlib import Path


def emit(dispatch, groups, stage, out):
    if dispatch['schema'] != 'dsrom.S81.C8.owner-source-dispatch.v1':
        raise ValueError('existing owner source dispatch required')
    if type(stage) is not int or not 0 <= stage < 81 or not groups:
        raise ValueError('actual native stage and nonempty TP4 schedule required')
    offers = dispatch['offers']
    selected = []
    for group in groups:
        if len(group) != 4 or any(type(i) is not int or not 0 <= i < len(offers) for i in group):
            raise ValueError('owner TP4 group needs four actual offer indices')
        ranks = {}
        for i in group:
            offer = offers[i]
            rank = offer['die_id'] % 4
            if offer['die_id'] // 4 != stage or rank in ranks:
                raise ValueError('selected offer native stage/rank mismatch')
            if offer['stage'] != stage or offer['rank'] != rank or not offer['node']:
                raise ValueError('source descriptor and physical offer differ')
            ranks[rank] = offer
        first = ranks[0]
        context = ('identity', 'token', 'position', 'user', 'epoch')
        if any(any(r[name] != first[name] for name in context) for r in ranks.values()):
            raise ValueError('TP4 source context mismatch')
        selected.append([ranks[r] for r in range(4)])
    lines = ['#include "s81_source_caller_plan.hpp"',
             'DsromS81SourcePlan dsrom_s81_bind_source(DsromS81Runtime& runtime) {',
             f'  if(runtime.stage!={stage})throw std::runtime_error("selected source plan stage mismatch");',
             '  DsromS81SourcePlan plan;']
    for group in selected:
        lines += ['  {', '    DsromS81SourceGroup group;']
        for rank, offer in enumerate(group):
            values = [str(offer['die_id'])] + [str(offer[k])+'u' for k in
                      ('token', 'position', 'user', 'epoch', 'entry')] + [str(offer['identity'])+'ull']
            node = json.dumps(offer['node'], ensure_ascii=True)
            lines += [f'    group.ranks[{rank}].offer = {{{", ".join(values)}}};',
                      f'    group.ranks[{rank}].source_node = {node};',
                      f'    dsrom_s81_bind_inputs(runtime,group.ranks[{rank}],{node});',
                      f'    dsrom_s81_bind_receipts(runtime,group.ranks[{rank}],{node});']
        lines += ['    plan.groups.push_back(std::move(group));', '  }']
    lines += ['  return plan;', '}']
    out = Path(out)
    with out.open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dispatch', type=Path, required=True)
    p.add_argument('--groups', type=Path, required=True,
                   help='owner ordered list of four offer indices for each TP4 group')
    p.add_argument('--stage', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print(emit(json.loads(a.dispatch.read_text()), json.loads(a.groups.read_text()), a.stage, a.out))


if __name__ == '__main__':
    main()
