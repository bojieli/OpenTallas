#!/usr/bin/env python3
"""Run one corrected GEN while preserving pre-mutation SSTN source/usage evidence.

No submission or route is performed. Run only through the fleet admission guard.
The first legacy-predicate rejection on this current model becomes a fixture.
The old c26k3 traceback did not identify its station; do not infer that identity.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy
import re
import resource
import shlex
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--options', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    evidence = out / 'sstn_entry'; evidence.mkdir(exist_ok=True)
    sys.path.insert(0, str(root / 'tools'))
    from s81 import sstn_split as split
    original = split.expand
    calls = 0

    def diagnostic(model, usage, mapping, views):
        nonlocal calls
        calls += 1
        selected = [i for i in model['insts'] if i.kind == 'sstn' and 'x2i' in usage.get(i.name, {})]
        records = []
        first = None
        for inst in selected:
            ports = usage[inst.name]
            missing = sorted(p for p, (d, _) in split.BASE_PORTS.items() if d == 'output' and p not in ports)
            role = 'dsfd_sstn_' + ''.join(k for k in ('e0', 'e1', 'c0', 'c1', 'si', 'nf', 'qt') if k in ports) + '_x2'
            record = dict(instance=inst.name, role=role, usage=ports, absent_outputs=missing)
            records.append(record)
            if missing and first is None:
                first = (inst, record)
        selected_names = {inst.name for inst in selected}
        active_bits = 0
        for bid, cls, width, eps in model['buses']:
            for name, port in eps:
                if name in selected_names:
                    match = re.search(r'\[(\d+)(?::(\d+))?\]', port)
                    active_bits += int(match[2] or match[1]) - int(match[1]) + 1 if match else width
        metadata = dict(entry_active_terminal_bit_occurrences=active_bits,
                        entry_max_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                        schema='s81-sstn-source-usage-entry-v1', generator_sha256=sha(root/'tools/dsrom_s81_fulldie.py'),
                        transform_sha256=sha(root/'tools/s81/sstn_split.py'), options_sha256=sha(args.options),
                        call=calls, selected=len(selected), records=records)
        (evidence/f'entry_{calls}.json.gz').write_bytes(gzip.compress(json.dumps(metadata).encode(), mtime=0))
        if first:
            inst, record = first
            station = {p: getattr(inst, p) for p in ('name', 'master', 'kind', 'x', 'y', 'w', 'h', 'orient', 'region', 'domain')}
            if hasattr(inst, 'power_w'):
                station['power_w'] = inst.power_w
            buses = []
            for bid, cls, width, eps in model['buses']:
                if not any(n == inst.name for n, p in eps):
                    continue
                # Keep actual source/terminal names at the component boundary.
                # Other shared-net loads do not change this station's bit ABI.
                kept = [ep for j, ep in enumerate(eps) if j == 0 or ep[0] == inst.name]
                if eps[0][0] == inst.name:
                    kept += next(([ep] for ep in eps[1:] if ep[0] != inst.name), [])
                buses.append((bid, cls, width, kept))
            fixture = dict(schema='s81-sstn-actual-failing-instance-v1', legacy_rejection='SSTN split unsupported absent base output',
                           historical_instance_identity='UNKNOWN: old c26k3 exception omitted instance; this fixture is the legacy predicate on the current model',
                           legacy_predicate_match=record, station=station, usage={inst.name: record['usage']}, buses=buses,
                           mapping=mapping, views={leaf['master']: {k: views[leaf['master']][k] for k in ('w', 'h', 'lef') if k in views[leaf['master']]}
                                                   for leaf in mapping['leaves'].values()}, source=metadata)
            (evidence/f'legacy_predicate_fixture_{calls}.json').write_text(json.dumps(fixture, indent=2)+'\n')
            print('OT_SSTN_LEGACY_PREDICATE ' + json.dumps(record), flush=True)
        try:
            result = original(model, usage, mapping, views)
        except Exception as exc:
            (evidence/f'corrected_failure_{calls}.json').write_text(json.dumps(dict(type=type(exc).__name__, message=str(exc)), indent=2)+'\n')
            raise
        model['sstn_split']['post_expand_max_rss_mb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
        (evidence/f'corrected_expansion_{calls}.json').write_text(json.dumps(model['sstn_split'], indent=2)+'\n')
        print('OT_SSTN_CORRECTED_EXPANSION ' + json.dumps(dict(call=calls, instances=model['sstn_split']['instances'],
              conserved=model['sstn_split']['conserved_active_terminal_bits'],
              clock_reset_duplicates=model['sstn_split']['duplicated_clock_reset_terminal_bits'])), flush=True)
        return result

    split.expand = diagnostic
    sys.argv = [str(root/'tools/dsrom_s81_fulldie.py'), *shlex.split(args.options.read_text()), '--out', str(out)]
    runpy.run_path(str(root/'tools/dsrom_s81_fulldie.py'), run_name='__main__')


if __name__ == '__main__':
    main()
