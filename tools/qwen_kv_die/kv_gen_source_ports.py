#!/usr/bin/env python3
"""Recover exact die-port directions from the selected strict-bind RTL.

An unbound geometric frame's INOUT is not proof of a bidirectional RTL port.
Use the existing exact bit-bundle mapping and selected source, never names.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from die_port_bind import parse_modules
from kv_gen_safety import bits, INST, CONN


def export(case, records, root, snapshots=None):
    bp, pp = records / 'bound_netlist.json', records / 'port_bind_v2.json'
    bound, bind = json.loads(bp.read_text()), json.loads(pp.read_text())
    sha = hashlib.sha256((case / 'die.v').read_bytes()).hexdigest()
    if bound['die_sha256'] != sha:
        raise ValueError('strict binder describes another die netlist')
    if bind['verdict'] != 'PASS' or bind.get('failing'):
        raise ValueError('source directions require a passing exact strict bind')
    die_text = (case / 'die.v').read_text()
    wire_widths = {n: int(hi) + 1 for hi, n in re.findall(r'wire\s+\[(\d+):0\]\s+(\S+);', die_text)}
    die_widths = {}
    for line in die_text.splitlines():
        match = INST.match(line)
        if not match or match[1] not in bound['masters']:
            continue
        for port, expr in CONN.findall(match[3]):
            width = len(bits(expr, wire_widths))
            key = (match[1], port)
            if key in die_widths and die_widths[key] != width:
                raise ValueError(f'{key}: inconsistent structural port width')
            die_widths[key] = width
    sources, masters, cache, hashes = {}, {}, {}, {}
    for die_master, ent in bound['masters'].items():
        name = ent['module']
        selected = bind['masters'][name]
        if selected['verdict'] != 'PASS' or selected.get('ambiguous_defs'):
            raise ValueError(f'{die_master}: source selection not proven')
        path = Path(selected['rtl'])
        if not path.is_absolute():
            path = root / path
        original = str(path)
        expected = None
        if snapshots is not None and original not in snapshots:
            raise ValueError(f'{die_master}: source snapshot manifest is incomplete: {original}')
        if snapshots and original in snapshots:
            expected = snapshots[original]['sha256']
            path = Path(snapshots[original]['path'])
        if path not in cache:
            raw = path.read_bytes()
            hashes[path] = hashlib.sha256(raw).hexdigest()
            cache[path] = parse_modules(raw.decode(), str(path))
        if expected and hashes[path] != expected:
            raise ValueError(f'{die_master}: source snapshot hash mismatch')
        sources[original] = hashes[path]
        matches = [m for m in cache[path] if m.name == name]
        if len(matches) != 1:
            raise ValueError(f'{die_master}: exact source has {len(matches)} definitions of {name}')
        mod = matches[0]
        envs = [mod.env(json.loads(p)) for p in selected.get('param_sets', {})] or [mod.env(ent.get('parameters'))]
        widths = {}
        for port, (direction, _) in mod.ports.items():
            values = {mod.width(port, env) for env in envs}
            if len(values) != 1 or None in values or direction not in ('input', 'output', 'inout'):
                raise ValueError(f'{die_master}/{port}: unresolved actual direction/width')
            widths[port] = values.pop()
        ports = {}
        bundles = ent.get('bundles') or {}
        if bundles:
            for bundle in bundles.values():
                actual = []
                for rp in bundle['rtl_ports']:
                    actual.extend([mod.ports[rp][0].upper()] * widths[rp])
                if len(actual) != bundle['die_bits'] or len(actual) != bundle['rtl_bits']:
                    raise ValueError(f'{die_master}: source bundle bit count differs from exact bind')
                dps = bundle['die_ports']
                offset = 0
                for dp in dps:
                    width = die_widths[die_master, dp]
                    ports[dp] = actual[offset:offset+width]
                    offset += width
                if offset != len(actual):
                    raise ValueError(f'{die_master}: split die-port widths differ from exact bundle')
        else:
            ports = {port: [mod.ports[port][0].upper()] * width for port, width in widths.items()}
        masters[die_master] = dict(module=name, source=original, ports=ports)
    return dict(schema='opentallas.kv_gen_source_ports.v1', die_sha256=sha, masters=masters,
                source_sha256=sources, record_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (bp, pp)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--records', type=Path, required=True)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--source-snapshots', type=Path, help='explicit original-path -> {path,sha256} immutable copy manifest')
    a = ap.parse_args()
    out = a.case / 'gen_source_ports.json'
    out.unlink(missing_ok=True)
    doc = export(a.case, a.records, a.root, json.loads(a.source_snapshots.read_text()) if a.source_snapshots else None)
    if a.source_snapshots:
        doc['source_snapshots_sha256'] = hashlib.sha256(a.source_snapshots.read_bytes()).hexdigest()
    out.write_text(json.dumps(doc, separators=(',', ':')) + '\n')
    print(f"KV_GEN_SOURCE_PORTS masters={len(doc['masters'])} sources={len(doc['source_sha256'])}")


if __name__ == '__main__':
    main()
