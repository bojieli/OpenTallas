#!/usr/bin/env python3
"""Apply the approved HEAD source/endpoint delta to the current infrastructure plan.

Moves the declared HEAD manifest supplement into the owning types' source closure,
sets the measured copy-B burst depth to two, and names the physical core entry pin.
Geometry, bus widths and schedule latency are preserved.
"""
import argparse
import copy
import json
import re
from pathlib import Path


def apply(plan, root, supplement):
    out = copy.deepcopy(plan)
    extras = [s.split('#')[0].strip() for s in supplement.splitlines()
              if s.split('#')[0].strip()]
    definitions = {}
    for src in extras:
        text = (root / src).read_text()
        definitions[src] = re.findall(r'\bmodule\s+(\w+)', text)
        if not definitions[src]:
            raise ValueError('supplement defines no module: ' + src)
    report = dict(sources={}, copy_b=[], taps=[])
    assigned = set()
    for tn, ty in out['partition_types'].items():
        sources = ty.setdefault('sources', [])
        added = []
        while True:
            text = '\n'.join((root / s).read_text() for s in sources)
            newly = [s for s in extras if s not in sources and
                     any(re.search(r'\b' + re.escape(m) + r'\b', text)
                         for m in definitions[s])]
            if not newly:
                break
            sources.extend(newly)
            added.extend(newly)
        if added:
            report['sources'][tn] = added
        assigned.update(s for s in extras if s in sources)
        for c in ty.get('contents', []):
            if c['module'] == 'ot_s81hd_mesh_ep_core':
                c.setdefault('params', {})['BQ'] = 2
                report['copy_b'].append(tn)
        for tap in ty.get('clock', {}).get('taps', []):
            if tap.get('kind') == 'core' and tap['name'].endswith('.clk'):
                tap['name'] = tap['name'][:-3] + 'ft_mstrap_i'
                report['taps'].append([tn, tap['name']])
    missing = set(extras) - assigned
    if missing:
        raise ValueError('supplement has no source consumer: ' + repr(sorted(missing)))
    return out, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--root', type=Path, default=Path('.'))
    ap.add_argument('--supplement', type=Path,
                    default=Path('tools/s81_head/head_portbind_extra.f'))
    ap.add_argument('--report', type=Path)
    args = ap.parse_args()
    plan, report = apply(json.loads(args.plan.read_text()), args.root,
                         args.supplement.read_text())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2) + '\n')
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
