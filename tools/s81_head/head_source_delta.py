#!/usr/bin/env python3
"""Apply the approved HEAD source/endpoint delta to the current infrastructure plan.

Moves the declared HEAD manifest supplement into the owning types' source closure,
sets the measured copy-B burst depth to two, and names the physical core entry pin.
Geometry, bus widths and schedule latency are preserved.
"""
import argparse
import copy
import json
import os
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
    report = dict(sources={}, copy_b=[], taps=[], source_profiles=[])
    assigned = set()
    for tn, ty in out['partition_types'].items():
        sources = list(ty.get('sources', []))
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
            ty['sources'] = sources
            report['sources'][tn] = added
        assigned.update(s for s in extras if s in sources)
        if any(s.endswith('/ot_s81ph_link_ep_safe4.sv') for s in sources):
            defines = ty.setdefault('verilog_defines', [])
            for token in ('OT_COLL_NATIVE32', 'OT_COLL_NATIVE32_OFF'):
                if token not in defines:
                    defines.append(token)
            report['source_profiles'].append(tn)
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


def rebase_pin_assets(plan, source, target, root):
    rebased = []
    for ty in plan['partition_types'].values():
        for core in ty.get('hard_cores', []):
            if core.get('pins_file'):
                old = core['pins_file']
                asset = (source.parent / old).resolve()
                asset.relative_to(root.resolve())
                if not asset.is_file():
                    raise ValueError('missing plan pin asset: ' + str(asset))
                core['pins_file'] = os.path.relpath(asset, target.parent.resolve())
                if core['pins_file'] != old:
                    rebased.append([old, core['pins_file']])
    return rebased


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
    # pins_file is relative to the plan directory (sources remain repo-relative).
    # A candidate exported under results/ must still read the original pin asset.
    report['plan_relative_pin_assets'] = rebase_pin_assets(plan, args.plan, args.out, args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2) + '\n')
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
