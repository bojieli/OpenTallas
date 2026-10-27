#!/usr/bin/env python3
"""Retarget centre-entry clock taps after an HBM hub replication/placement delta.

Opt-in plan postpass: clones the original per-core clock contract onto each exact
replica, at its new geometric centre. This repairs plan connectivity only; native
core pins and the die clock still need their master-plan rebuild. No RTL changes.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path


def retarget_type(t):
    clock = t.get('clock', {})
    if clock.get('core_taps') != 'early':
        raise ValueError('expected explicit core-tap clock contract')
    bases = {re.sub(r'__q\d+$', '', h['inst']) for h in t['hard_cores']}
    bases.update(h['inst'] for h in t['hard_cores'])
    templates = {}
    for tap in clock.get('taps', []):
        if tap.get('kind') != 'core' or 'core_group' in tap:
            raise ValueError('retarget ungrouped core taps before forming clock groups')
        candidates = [n for n in bases if tap['name'] == n or tap['name'].startswith(n + '.')]
        if not candidates:
            raise ValueError(f"{tap['name']}: no surviving core or replica base")
        inst = max(candidates, key=len)
        templates.setdefault(inst, []).append((tap['name'][len(inst):], tap))
    replacement = []
    moved = []
    for h in t['hard_cores']:
        inst = h['inst']
        original = re.sub(r'__q\d+$', '', inst)
        contracts = templates.get(inst, templates.get(original))
        if not contracts:
            raise ValueError(f'{inst}: no source clock contract (base {original})')
        for suffix, source in contracts:
            if source.get('budget_owner') not in (None, h['module']):
                raise ValueError(f'{inst}: clock contract module differs from hard core')
            target = copy.deepcopy(source)
            xy = [round(o + w / 2, 3) for o, w in zip(h['origin_um'], h['outline_um'])]
            target.update(name=inst + suffix, xy=xy)
            target['note'] = ('HBM hub post-placement clock retarget: source ' + source['name'] +
                              '; centre entry; native core and die tree rebuild still required')
            replacement.append(target)
            moved.append(dict(name=target['name'], source=source['name'], old_xy=source['xy'], new_xy=xy))
    if len({tap['name'] for tap in replacement}) != len(replacement):
        raise ValueError('duplicate retargeted clock names')
    clock['taps'] = replacement
    return dict(cores=len(t['hard_cores']), old_taps=sum(map(len, templates.values())), new_taps=len(replacement), moves=moved)


def run(src, out, types):
    raw = Path(src).read_bytes()
    p = json.loads(raw)
    report = dict(source_sha256=hashlib.sha256(raw).hexdigest(), types={})
    for tn in types:
        report['types'][tn] = retarget_type(p['partition_types'][tn])
    Path(out).write_text(json.dumps(p, indent=1) + '\n')
    report['plan_sha256'] = hashlib.sha256(Path(out).read_bytes()).hexdigest()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('--out', required=True)
    ap.add_argument('--types', nargs='+', default=['q_hub_nw', 'q_hub_ne'])
    a = ap.parse_args()
    print(json.dumps(run(a.plan, a.out, a.types), indent=1))


if __name__ == '__main__':
    main()
