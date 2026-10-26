#!/usr/bin/env python3
"""Compose S81 B2 signal deltas without moving interfaces or adding alignment.

Base is the stations-v4+PHY-control-pin plan (B2 C+E). Replay TYPE-REDUCE-2
(D) from its parent, then A25 internal FT sites (B) from A8. Reject conflicting
changes before writing anything. All leaf-template core OBS stay capped at M5.
This emits a candidate; infra-first, published-size PHY geometry, SRAM re-kit,
strict bind and token/calendar gates remain separate obligations.
"""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

HARD_FIELDS = frozenset(('lef', 'pins_file', 'orient', 'track_offset_um', 'note'))
SITE_FIELDS = frozenset(('bit_sites_um', 'regs_um', 'bit_site_cell_um'))
MISSING = object()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_fields(target, before, after, allowed, context, counts):
    changes = [key for key in set(before) | set(after)
               if before.get(key, MISSING) != after.get(key, MISSING)]
    unexpected = set(changes) - allowed
    if unexpected:
        raise ValueError(f'{context}: unapproved fields {sorted(unexpected)}')
    for key in changes:
        old, new, live = before.get(key, MISSING), after.get(key, MISSING), target.get(key, MISSING)
        if live != old and live != new:
            raise ValueError(f'{context}.{key}: conflicts with base')
        if new is MISSING:
            target.pop(key, None)
        else:
            target[key] = copy.deepcopy(new)
        counts[key] += 1


def indexed(items, key, context):
    out = {item[key]: item for item in items}
    if len(out) != len(items):
        raise ValueError(f'{context}: duplicate {key}')
    return out


def apply_leaf(target, before, after):
    counts = Counter()
    for name, typ in after['partition_types'].items():
        prior = indexed(before['partition_types'].get(name, {}).get('hard_cores', []), 'inst', name)
        changed = [h for h in typ.get('hard_cores', []) if h != prior.get(h['inst'])]
        if not changed:
            continue
        live = indexed(target['partition_types'][name].get('hard_cores', []), 'inst', name)
        for core in changed:
            inst = core['inst']
            replay_fields(live[inst], prior[inst], core, HARD_FIELDS, f'{name}.{inst}', counts)
    return dict(counts)


def apply_sites(target, before, after):
    counts = Counter()
    for name, typ in after['partition_types'].items():
        old = before['partition_types'].get(name)
        if old == typ:
            continue
        if old is None:
            raise ValueError(f'A25 adds type {name}')
        # A25 is deliberately an internal-site delta; any interface difference fails.
        lhs, rhs = copy.deepcopy(old), copy.deepcopy(typ)
        old_slots, new_slots = lhs.pop('ft_slots', []), rhs.pop('ft_slots', [])
        live_non_sites = copy.deepcopy(target['partition_types'][name])
        live_non_sites.pop('ft_slots', None)
        if lhs != rhs and live_non_sites != rhs:
            raise ValueError(f'A25 changes non-site fields not already present in {name}')
        if len(old_slots) != len(new_slots):
            raise ValueError(f'A25 changes slot count in {name}')
        live_slots = target['partition_types'][name].get('ft_slots', [])
        if len(live_slots) != len(old_slots):
            raise ValueError(f'base slot count differs in {name}')
        for i, (a, b) in enumerate(zip(old_slots, new_slots)):
            replay_fields(live_slots[i], a, b, SITE_FIELDS, f'{name}.ft_slots[{i}]', counts)
    return dict(counts)


def compose(base, leaf_before, leaf_after, sites_before, sites_after):
    result = copy.deepcopy(base)
    report = {'leaf_template_fields': apply_leaf(result, leaf_before, leaf_after),
              'a25_site_fields': apply_sites(result, sites_before, sites_after)}
    return result, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ('base', 'leaf-before', 'leaf-after', 'sites-before', 'sites-after', 'out', 'report'):
        ap.add_argument('--' + arg, required=True, type=Path)
    args = ap.parse_args()
    paths = {key: getattr(args, key) for key in ('base', 'leaf_before', 'leaf_after', 'sites_before', 'sites_after')}
    inputs = {key: json.loads(path.read_text()) for key, path in paths.items()}
    result, report = compose(**inputs)
    report['inputs'] = {key: {'path': str(path), 'sha256': digest(path)} for key, path in paths.items()}
    report['obligations'] = ['Copy D template LEFs/pins into output root and run delta_tplcap_1026.py there.',
                             'Published-size PHY re-lay, SRAM re-kit, infra-first PG/clock/reset, G0C/bind/token gates.']
    encoded = json.dumps(result, separators=(',', ':')) + '\n'
    report['plan_sha256'] = hashlib.sha256(encoded.encode()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(encoded)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
