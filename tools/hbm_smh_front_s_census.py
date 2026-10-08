#!/usr/bin/env python3
"""Summarize an immutable front_s endpoint census for a source-bound ECO plan."""
import argparse
import hashlib
import gzip
import json
import re
from pathlib import Path


def read_text(path):
    if path.exists():
        return path.read_text()
    with gzip.open(str(path) + '.gz', 'rt') as stream:
        return stream.read()


def slacks(report):
    return [float(v) for v in re.findall(r'^\s*([-\d.]+)\s+slack \(', report, re.M)]


def summarize(root):
    receipt = json.loads((root / 'complete.json').read_text())
    if receipt['status'] != 'PASS':
        raise ValueError('Census did not complete')
    topology = json.loads(next(line.split(' ', 1)[1] for line in
        read_text(root / 'topology.log').splitlines()
        if line.startswith('OUTPUT_TOPOLOGY_JSON ')))
    records = {p['port']: dict(port=p['port'], topology=p, paths={}) for p in topology['outputs']}
    internal = {}
    for corner in ('ff', 'ss'):
        text = read_text(root / f'outputs_{corner}.log')
        if '[ERROR' in text:
            raise ValueError('Tool error in census log')
        for m in re.finditer(r'OT_OUTPUT_BEGIN (\S+) (min|max)\n(.*?)OT_OUTPUT_END', text, re.S):
            port, check, report = m.groups()
            values = slacks(report)
            if values:
                records[port]['paths'][corner + '_' + check] = dict(slack_ps=min(values))
        if corner == 'ff':
            for m in re.finditer(r'OT_INTERNAL_BEGIN (\S+) ([-\d.]+)\n(.*?)OT_INTERNAL_END', text, re.S):
                pin, value, report = m.groups()
                internal[pin] = dict(pin=pin, slack_ps=float(value), ff_report=report)
        else:
            for m in re.finditer(r'OT_INTERNAL_SS_BEGIN (\S+)\n(.*?)OT_INTERNAL_SS_END', text, re.S):
                pin, report = m.groups()
                values = slacks(report)
                if pin not in internal or not values:
                    raise ValueError('Internal SS endpoint mismatch: ' + pin)
                internal[pin].update(ss_setup_ps=min(values), ss_report=report)
    for row in records.values():
        if not all(k in row['paths'] for k in ('ff_min', 'ss_max')):
            raise ValueError('Unconstrained or missing output: ' + row['port'])
    for row in internal.values():
        if 'ss_setup_ps' not in row:
            raise ValueError('Missing SS evidence: ' + row['pin'])
    return receipt, list(records.values()), list(internal.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--census', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        ap.error('--out must be new')
    receipt, outputs, internal = summarize(a.census)
    eligible = [row for row in outputs if row['paths']['ff_min']['slack_ps'] < 25]
    summary = dict(source=receipt['source'], outputs=len(outputs), outputs_below25=len(eligible),
        internal_below25=len(internal),
        eligible_output_min_ss_ps=min((row['paths']['ss_max']['slack_ps'] for row in eligible), default=None),
        eligible_output_min_ff_ps=min((row['paths']['ff_min']['slack_ps'] for row in eligible), default=None),
        internal_min_ss_ps=min((row['ss_setup_ps'] for row in internal), default=None),
        internal_min_ff_ps=min((row['slack_ps'] for row in internal), default=None),
        input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.census.iterdir()
                      if p.is_file() and p.suffix in ('.json', '.log', '.gz')},
        qualification='Endpoint census only; new delay chains require fresh extracted SS/FF')
    a.out.mkdir(parents=True)
    for name, obj in [('all_outputs.json', outputs), ('outputs_below25.json', eligible),
                      ('internal_below25.json', internal), ('summary.json', summary)]:
        (a.out / name).write_text(json.dumps(obj, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
