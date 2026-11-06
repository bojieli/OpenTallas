"""Replay the exact proved SU_l1 two-type event onto an unchanged selected base."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'sidecar', 'out-plan', 'out-sidecar'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    load = lambda path: json.loads(path.read_text())
    plan, sidecar = load(args.plan), load(args.sidecar)
    guards = load(root / 'base_guards.json')
    types = load(root / 'selected_types.json')
    entries = load(root / 'collector_entries.json')
    if set(guards) != set(types) or set(types) != set(entries):
        raise ValueError('event type/collector/guard sets differ')
    for name, guard in guards.items():
        if digest(plan['partition_types'][name]) != guard['plan_type_sha256']:
            raise ValueError(name + ': selected base type changed; review composition')
        if digest(sidecar['collector']['types'][name]) != guard['collector_type_sha256']:
            raise ValueError(name + ': selected collector changed; review composition')
    for name in guards:
        plan['partition_types'][name] = types[name]
        sidecar['collector']['types'][name] = entries[name]
    for target, value in ((args.out_plan, plan), (args.out_sidecar, sidecar)):
        target.write_text(json.dumps(value, indent=1) + '\n')
    print(json.dumps({'types': sorted(guards), 'data_cycles': 0, 'boot_cycles': 0}))


if __name__ == '__main__':
    main()
