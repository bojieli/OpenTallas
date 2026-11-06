#!/usr/bin/env python3
"""Capture actual CTS source-root bindings into a mapped station source.

The two TSVs come from the retained placed/CTS ODBs. This removes clock-tree
buffer implementation from the interface, preserving its traced source root
at every existing sequential clock pin. No data/reset connection is changed.
The physical consumer must retain the original root timing frames and guards.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def root_bit(module, root):
    ports = module['ports']
    if root in ports:
        p = ports[root]
        if p['direction'] != 'input' or len(p['bits']) != 1:
            raise ValueError('source root must be an explicit scalar input: ' + root)
        return p['bits'][0]
    match = re.fullmatch(r'(.+)\[(\d+)\]', root)
    if not match or match[1] not in ports:
        raise ValueError('missing exact source root port: ' + root)
    p = ports[match[1]]
    index = int(match[2]) - p.get('offset', 0)
    if p.get('upto'):
        index = len(p['bits']) - 1 - index
    if p['direction'] != 'input' or not 0 <= index < len(p['bits']):
        raise ValueError('invalid source root bit: ' + root)
    return p['bits'][index]


def load_rows(path, cts=False):
    rows = {}
    for line in Path(path).read_text().splitlines():
        n, master, pin, net, field = line.split('\t')
        if n in rows:
            raise ValueError('duplicate sequential clock pin: ' + n)
        rows[n] = dict(master=master, pin=pin,
                       root=net if cts else field, parity=int(field) if cts else 0)
    return rows


def capture(source, module_name, placed_rows, cts_rows):
    if set(placed_rows) != set(cts_rows):
        raise ValueError('placed/CTS sequential instance inventories differ')
    m = source['modules'][module_name]
    masters, roots, changes = set(), {}, 0
    # OpenDB's Verilog writer removes the Yosys backslash quoting on names.
    canonical = {}
    for source_name in m['cells']:
        key = source_name.replace(chr(92), '')
        if key in canonical:
            raise ValueError('ambiguous native/source identifier after unquoting: ' + key)
        canonical[key] = source_name
    aliases = 0
    for name, old in placed_rows.items():
        actual = cts_rows[name]
        if actual['parity'] != 0:
            raise ValueError('inverted clock path needs explicit phase support: ' + name)
        if old['pin'] != actual['pin']:
            raise ValueError('sequential clock pin identity changed: ' + name)
        source_name = canonical.get(name.replace(chr(92), ''))
        c = m['cells'].get(source_name)
        aliases += source_name != name
        if c is None or c['type'] != old['master']:
            raise ValueError('mapped source master/instance differs from placed ODB: ' + name)
        family = lambda s: re.split(r'x(?:\d|p)', s, maxsplit=1)[0]
        if family(old['master']) != family(actual['master']):
            raise ValueError('CTS changed sequential edge/state class: ' + name)
        pin = old['pin']
        if c['connections'].get(pin) is None or len(c['connections'][pin]) != 1:
            raise ValueError('missing/non-scalar mapped clock pin: ' + name)
        candidates = []
        for r in old['root'].split(','):
            try:
                b = root_bit(m, r)
            except ValueError:
                continue  # output-only forwarded aliases are not input roots
            if b == c['connections'][pin][0]:
                candidates.append(r)
        if len(candidates) != 1:
            raise ValueError('placed clock root does not match exact mapped source: ' + name)
        target = root_bit(m, actual['root'])
        changes += c['connections'][pin] != [target]
        c['connections'][pin] = [target]
        masters.add(old['master'])
        roots[actual['root']] = roots.get(actual['root'], 0) + 1
    return dict(schema='opentallas.station_native_clock_capture.v1',
                module=module_name, sequential_instances=len(cts_rows),
                sequential_masters=sorted(masters), roots=roots,
                changed_clock_bindings=changes, native_name_unquotings=aliases, inversion_parity=0,
                data_reset_changes=0, cycles_added=0,
                status='ACTUAL_CTS_ROOT_CAPTURE; inherited timing frames/guards and physical rebuild still owed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('placed'); p.add_argument('cts')
    p.add_argument('--module', required=True); p.add_argument('--out', required=True)
    p.add_argument('--placed-odb', required=True); p.add_argument('--cts-odb', required=True)
    a = p.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    source = json.loads(Path(a.source).read_text())
    receipt = capture(source, a.module, load_rows(a.placed), load_rows(a.cts, True))
    receipt['inputs_sha256'] = {str(x): sha(x) for x in (a.source, a.placed, a.cts, a.placed_odb, a.cts_odb)}
    target = out / 'native_bound.json'
    target.write_text(json.dumps(source) + '\n')
    receipt['bound_sha256'] = sha(target)
    (out / 'clock_capture.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('inputs_sha256', 'roots')}))


if __name__ == '__main__':
    main()
