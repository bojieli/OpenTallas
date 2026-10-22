"""Review proposal only: compare complete netlists modulo positive-BUF IDs/order.

Never used for admission. Refuses attributes, unsupported buffer syntax, missing
or extra contacts, clocks, state, and functions other than the sole input pin.
Everything outside the reviewed BUFx cell statements is retained byte for byte.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


BUF = re.compile(r'^  (BUFx\w+) (_\d+_) \(\n(.*?)\n  \);', re.M | re.S)
PIN = re.compile(r'^    \.(\w+)\(([^()]+)\)(,?)$')


def canonical(raw, roles):
    text = raw.decode()
    pieces, counts = [], []
    for module in re.split(r'(?=^module )', text, flags=re.M):
        rows, names = [], set()

        def replace(match):
            master, instance, body = match.groups()
            if instance in names:
                raise ValueError('duplicate buffer identity')
            names.add(instance)
            prefix = module[module.rfind(';', 0, match.start()) + 1:match.start()]
            if '(*' in prefix or '*)' in prefix:
                raise ValueError('buffer attribute is unsupported; preserve its association')
            role = roles.get(master)
            if not role or role['sequential'] or role['bus_order']:
                raise ValueError('unsupported buffer master ' + master)
            pins = role['pins']
            ins = [p for p, r in pins.items() if r['direction'] == 'input']
            outs = [p for p, r in pins.items() if r['direction'] == 'output']
            if len(pins) != 2 or len(ins) != 1 or len(outs) != 1 or any(p['clock'] for p in pins.values()):
                raise ValueError('not an actual unary non-clock buffer ' + master)
            function = re.sub(r'[\s()]', '', pins[outs[0]]['function'] or '')
            if function != ins[0]:
                raise ValueError('not an actual positive BUF function ' + master)
            contacts = [PIN.fullmatch(line) for line in body.splitlines()]
            if len(contacts) != 2 or any(c is None for c in contacts):
                raise ValueError('unsupported buffer connection statement')
            if {c[1] for c in contacts} != set(pins) or contacts[0][3] != ',' or contacts[1][3]:
                raise ValueError('missing/extra/duplicate buffer contact')
            # Include master plus the COMPLETE exact contact body and multiplicity.
            # Only this statement's instance ID and position among other BUF
            # statements are omitted; net names and all non-BUF context survive.
            rows.append((master, body))
            return '  __REVIEWED_POSITIVE_BUF_STATEMENT__;'

        outside = BUF.sub(replace, module)
        # Refuse any candidate BUFx instance that did not match the supported form.
        if re.search(r'^\s+BUFx\w+\s+\S+\s*\(', outside, re.M):
            raise ValueError('unsupported BUFx statement left in context')
        pieces.append(outside + '\n' + json.dumps(sorted(rows), separators=(',', ':')))
        counts.append(dict(count=len(rows), masters=dict(Counter(m for m, _ in rows))))
    return ''.join(pieces).encode(), counts


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--old-source', required=True)
    ap.add_argument('--new-source', required=True)
    ap.add_argument('--old-report', required=True)
    ap.add_argument('--new-report', required=True)
    ap.add_argument('--packet', required=True)
    ap.add_argument('--native-tool', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location('review_native_census', a.native_tool)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    old_report, new_report = [json.loads(Path(p).read_text()) for p in (a.old_report, a.new_report)]
    packet = json.loads(Path(a.packet).read_text())
    if old_report['liberty'] != new_report['liberty']:
        raise ValueError('actual Liberty bytes changed')
    roles, receipts = native.liberty_roles([r['path'] for r in old_report['liberty']])
    if receipts != old_report['liberty']:
        raise ValueError('loaded actual Liberty provenance differs')
    nodes = lambda r: [{k: n[k] for k in ('driver', 'driver_role', 'net', 'loads')} for n in r['violations']]
    if nodes(old_report) != nodes(new_report) or len(nodes(old_report)) != 15:
        raise ValueError('raw native node signature changed')
    if any(r['role_errors'] or r['max_dynamic_loads'] != 34 or r['status'] != 'FAIL'
           for r in (old_report, new_report)):
        raise ValueError('raw native classification changed')
    sources = {}
    for path, expected in packet['source_sha256'].items():
        hashes = [digest((Path(src) / path).read_bytes()) for src in (a.old_source, a.new_source)]
        if hashes != [expected, expected]:
            raise ValueError('source bytes changed: ' + path)
        sources[path] = expected
    raws = [Path(p).read_bytes() for p in (a.old, a.new)]
    canonical_rows = [canonical(raw, roles) for raw in raws]
    if canonical_rows[0] != canonical_rows[1]:
        raise ValueError('complete canonical context/contact/multiplicity differs')
    result = dict(scope='REVIEW_PROPOSAL_ONLY_NO_ADMISSION', equal=True,
                  raw_sha256=[digest(raw) for raw in raws], raw_bytes=[len(raw) for raw in raws],
                  canonical_sha256=digest(canonical_rows[0][0]), modules=canonical_rows[0][1],
                  source_sha256=sources, liberty=receipts, raw_native_nodes=nodes(old_report))
    Path(a.out).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('scope', 'equal', 'raw_sha256', 'canonical_sha256', 'modules')}))


if __name__ == '__main__':
    main()
