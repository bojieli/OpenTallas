#!/usr/bin/env python3
"""Generate diagnostic R8 landing pads for the three unique KV control/link partitions.

Usage: prepare_seams_2144.py PLAN RAW_BUS_GROUPS OUT_TABLE
The full R8 gate is intentionally not claimed: replicated PC token/epoch landing
constraints still require a structural repair. Compiler diagnostics consume the
actual emitted bus_groups, never this proposed table alone.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / 'tools/die_plan'))
import r8


def main(argv):
    plan, groups, dest = map(Path, argv)
    raw, bg = json.loads(plan.read_text()), json.loads(groups.read_text())
    r8.configure(['(?i)(^|_)(fault|flt)(_o|_q)?$', '^(afu|afv|afk|fault_i|fi)$'])
    members, _ = r8.solve(bg, raw, 'type', 'leaf')
    for m in members:
        m.pop('cls')
        if m['sink_part'] not in {'hub_C', 'hub_Wi', 'sys_c'}:
            m.update(pad=0, landed=m['bound'])
    summary = dict(padded_members=sum(bool(m['pad']) for m in members),
                   pad_flops=sum(r8.nbits(m['sink_bits']) * m['pad'] for m in members),
                   max_pad=max(m['pad'] for m in members))
    table = dict(schema=r8.SCHEMA, die=raw['die']['name'], replica='type', bus='leaf',
                 exempt=[x.pattern for x in r8.EXEMPT], bus_groups_die=bg.get('die'),
                 bus_groups_digest=r8.bg_digest(bg),
                 note='Diagnostic partial R8 repair of unique hub_C/hub_Wi/sys_c only; not full R8 or physical closure.',
                 summary=summary, members=members)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(table, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main(sys.argv[1:])
