#!/usr/bin/env python3
"""Check primitive identity and every pin relation after structural-copy mapping.

This is the combinational/one-edge correspondence part of the proof. It is
conditional on equal states of corresponding DFFs; the independent-state
cold-reset proof must establish that condition before the first active request.
No truth table or clock/reset sense is inferred or substituted here.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


def check(original, mapped, parser, record):
    spec = importlib.util.spec_from_file_location('certificate_textbook', parser)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    raw = original.read_bytes()
    if original.suffix == '.gz':
        raw = gzip.decompress(raw)
    assert hashlib.sha256(raw).hexdigest() == record['source_sha256']
    old, _ = m.flatten(m.parse_verilog(raw.decode()), None)
    new, _ = m.flatten(m.parse_verilog(mapped.read_text()), record['top'])
    oa, na = m.build(old, None), m.build(new, None)
    copies = {r['cell']: r['copies'] for r in record['copied_cells']}

    def resolve(g, a, x):
        inv, seen = False, set()
        while x in a['driver']:
            ci, pn = a['driver'][x]
            if ci < 0 or a['kind'][ci] != 'buf':
                break
            assert x not in seen, 'buffer cycle'
            seen.add(x)
            typ, _, pins = g.cells[ci]
            ins = [b for p, bits in pins.items() if a['pin_dir'][ci][p] == 'in' for b in bits]
            assert len(ins) == 1
            inv ^= bool(re.match('INV', typ, re.I))
            x = ins[0]
        return x, inv

    def logical_new(x):
        root, inv = resolve(new, na, x)
        if root <= 3:
            return root, inv
        ci, pn = na['driver'][root]
        if ci < 0:
            return old.ports[pn][1], inv
        match = re.fullmatch(r'u(\d+)_c(\d+)\.u_cell', new.cells[ci][1])
        assert match, ('unexpected primitive', new.cells[ci])
        oi = int(match[1])
        new_bits = new.cells[ci][2][pn]
        old_bits = old.cells[oi][2][pn]
        return old_bits[new_bits.index(root)], inv

    seen = set()
    for ci, (typ, name, pins) in enumerate(new.cells):
        if na['kind'][ci] == 'buf':
            continue
        match = re.fullmatch(r'u(\d+)_c(\d+)\.u_cell', name)
        assert match, ('unexpected primitive', typ, name)
        oi, replica = map(int, match.groups())
        assert 0 <= replica < copies.get(oi, 1)
        assert (oi, replica) not in seen
        seen.add((oi, replica))
        ot, on, op = old.cells[oi]
        assert typ == ot, ('cell function changed', typ, ot)
        assert set(pins) == set(op), ('pin interface changed', on)
        for pn, bits in pins.items():
            assert len(bits) == len(op[pn])
            assert na['pin_dir'][ci][pn] == oa['pin_dir'][oi][pn]
            if na['pin_dir'][ci][pn] == 'in':
                for got, want in zip(bits, op[pn]):
                    assert logical_new(got) == resolve(old, oa, want), ('input relation changed', name, pn)
    expected = {(ci, k) for ci in range(len(old.cells)) if oa['kind'][ci] != 'buf'
                for k in range(copies.get(ci, 1))}
    assert seen == expected, ('missing or extra primitives', len(seen), len(expected))
    assert set(old.ports) == set(new.ports)
    for pn, (direction, x) in old.ports.items():
        assert new.ports[pn][0] == direction
        if direction == 'output':
            assert logical_new(new.ports[pn][1]) == resolve(old, oa, x), ('output relation changed', pn)
    return dict(pass_primitive_and_pin_correspondence=True, checked_primitive_copies=len(seen),
                state_condition='corresponding primitive states equal; cold-reset proof required',
                source_sha256=record['source_sha256'], mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'mapped', 'parser', 'record', 'out'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    result = check(a.original, a.mapped, a.parser, json.loads(a.record.read_text()))
    a.out.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
