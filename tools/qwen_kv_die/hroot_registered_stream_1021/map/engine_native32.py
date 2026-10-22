#!/usr/bin/env python3
"""Generate an opt-in, source-pinned structural KV group with bounded drivers.

Input is the immutable pre-placement mapped s3/s4 source, never a repaired ODB.
Every replicated primitive retains its original type, D, clock and reset. BUF/INV
trees are resolved with polarity before partitioning terminal loads. Replication
propagates backward to the fixed point; an overloaded input refuses generation.

This generator is not a qualification: re-synthesis census and cold-boot
equivalence with independent initial register state remain required before gate.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import gzip
import importlib.util
import json
from pathlib import Path
import re
import sys


def ident(name):
    return name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', name) else '\\' + name + ' '


OUT_COPIES = {'done_v': 3}   # QKC-HROOT: done_v feeds 84 shell loads; each copy is its own driver replica
ALLOW_HEAVY = set()  # Every non-clock input, including reset, must obey the 32-load limit.


def generate(netlist, parser, expected, top, dest):
    raw = netlist.read_bytes()
    if netlist.suffix == '.gz':
        raw = gzip.decompress(raw)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError(f'input identity changed: {actual} != {expected}')
    spec = importlib.util.spec_from_file_location('kv_s5_textbook', parser)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    mods = m.parse_verilog(raw.decode())
    g, oldtop = m.flatten(mods, None)
    ports = mods[oldtop]
    a = m.build(g, None)
    clocks, _ = m.clock_nets(g, a)
    kinds, directions = a['kind'], a['pin_dir']
    live = [ci for ci in range(len(g.cells)) if kinds[ci] != 'buf']
    resolved = {}

    def resolve(x, visiting=None):
        if x in resolved:
            return resolved[x]
        d = a['driver'].get(x)
        if d is None or d[0] < 0 or kinds[d[0]] != 'buf':
            result = x, False
        else:
            ci = d[0]
            typ, _, pins = g.cells[ci]
            ins = [b for pn, bs in pins.items() if directions[ci][pn] == 'in' for b in bs]
            if len(ins) != 1:
                raise ValueError(f'not a unary buffer/inverter: {g.cells[ci]}')
            visiting = set() if visiting is None else visiting
            if x in visiting:
                raise ValueError('buffer/inverter cycle')
            visiting.add(x)
            root, inv = resolve(ins[0], visiting)
            result = root, inv ^ bool(re.match(r'INV', typ, re.I))
        resolved[x] = result
        return result

    inputs = {ci: [(pn, j, resolve(x)) for pn, bs in g.cells[ci][2].items()
                   if directions[ci][pn] == 'in' for j, x in enumerate(bs)] for ci in live}
    outputs = {ci: [x for pn, bs in g.cells[ci][2].items()
                    if directions[ci][pn] == 'out' for x in bs] for ci in live}
    external = [(name, resolve(x)) for name, (direction, x) in g.ports.items() if direction == 'output']
    count = {ci: 1 for ci in live}
    extra = Counter()
    out_extra = []
    for name, (root, inv) in external:
        if name in OUT_COPIES:
            d = a['driver'].get(root)
            if d is None or d[0] < 0:
                raise ValueError(f'output copy {name}: not driven by a cell')
            extra[d[0]] += OUT_COPIES[name] - 1
            out_extra.append((name, root, inv, d[0]))
    history = []
    while True:
        loads = Counter(root for _, (root, _) in external)
        for ci in live:
            for _, _, (root, _) in inputs[ci]:
                loads[root] += count[ci]
        changed = False
        for ci in live:
            if kinds[ci] == 'tie':
                continue
            want = max([1] + [(loads[x] + 31) // 32 for x in outputs[ci] if x not in clocks]) + extra[ci]
            if want > count[ci]:
                count[ci] = want
                changed = True
        history.append(sum(count.values()))
        if not changed:
            break
        if len(history) > len(live):
            raise ValueError('driver partition did not converge')
    port_copies = {}
    for name, (direction, x) in g.ports.items():
        if direction == 'input' and x not in clocks and loads[x] > 32:
            if name in ALLOW_HEAVY:
                continue
            port_copies[x] = (name, (loads[x] + 31) // 32)
    for ci in live:
        if kinds[ci] == 'macro' and count[ci] != 1:
            raise ValueError(f'macro {g.cells[ci][1]} needs a real registered landing, not duplicated storage')

    # Each structural primitive is behind a kept hierarchy boundary. In
    # particular, identical DFF copies must not disappear in opt_merge.
    shapes = {}
    for ci in live:
        typ, _, pins = g.cells[ci]
        shape = (typ, tuple((pn, len(bs), directions[ci][pn]) for pn, bs in pins.items()))
        shapes.setdefault(shape, f'{top}_cell_{len(shapes)}')
    extra_outs = [f'{nm}__c{k}' for nm, _, _, _ in out_extra for k in range(1, OUT_COPIES[nm])]
    extra_ports = [f'{nm}__c{k}' for x, (nm, kc) in sorted(port_copies.items(), key=lambda t: t[1][0]) for k in range(1, kc)]
    lines = ['`timescale 1ns/1ps', '// Generated by kv_grp_safe5.py; opt-in, NOT YET QUALIFIED.',
             f'// Immutable input sha256: {actual}', f'module {top} (',
             ',\n'.join('  ' + ident(p) for p in list(ports.ports) + extra_ports + extra_outs), ');']
    for p in extra_outs:
        lines.append(f'  output wire {p};')
    for p in extra_ports:
        lines.append(f'  input wire {p};')
    for p in ports.ports:
        size = '' if p not in ports.widths else '[%d:%d] ' % ports.widths[p]
        lines.append(f'  {ports.dirs[p]} wire {size}{ident(p)};')
    # All nets are scalar internally; top vector spelling alone retains ABI.
    wires = set()
    cursor = Counter()
    assignments = {}
    actual_loads = Counter()

    def root_wire(root, replica, inv=False):
        if root <= 3:
            val = ["1'b0", "1'b1", "1'bx", "1'bz"][root]
            return ('~' + val) if inv else val
        driver = a['driver'].get(root)
        if driver is None:
            raise ValueError(f'undriven net {g.net_name[root]}')
        ci = driver[0]
        if ci < 0:
            text = ident(driver[1].split('[')[0]) + ('[' + driver[1].split('[', 1)[1] if '[' in driver[1] else '')
            if root in port_copies and replica > 0:
                text = f'{port_copies[root][0]}__c{replica}'
        else:
            text = f'n{root}_c{replica}'
            wires.add(text)
        if inv:
            inverted = f'i{root}_c{replica}'
            wires.add(inverted)
            assignments[inverted] = '~' + text
            return inverted
        return text

    def consume(root, inv):
        driver = a['driver'].get(root)
        constant = root <= 3 or (driver is not None and driver[0] >= 0 and kinds[driver[0]] == 'tie')
        replica = 0 if constant or root in clocks or driver is None or (driver[0] < 0 and root not in port_copies) else cursor[root] // 32
        cursor[root] += 1
        if not constant and root not in clocks and not (driver is not None and driver[0] < 0 and g.net_name[root] in ALLOW_HEAVY):
            actual_loads[(root, replica)] += 1
        return root_wire(root, replica, inv)

    body = []
    manifest = []
    for ci in live:
        typ, name, pins = g.cells[ci]
        shape = (typ, tuple((pn, len(bs), directions[ci][pn]) for pn, bs in pins.items()))
        for replica in range(count[ci]):
            connections = []
            for pn, bs in pins.items():
                values = [consume(*resolve(x)) if directions[ci][pn] == 'in'
                          else root_wire(x, replica) for x in bs]
                value = values[0] if len(values) == 1 else '{' + ','.join(values) + '}'
                connections.append(f'.{ident(pn)}({value})')
            body.append(f'  {shapes[shape]} u{ci}_c{replica} (' + ','.join(connections) + ');')
        if count[ci] > 1:
            manifest.append(dict(cell=ci, original=name, type=typ, kind=kinds[ci], copies=count[ci]))
    for name, (root, inv) in external:
        base, _, tail = name.partition('[')
        output = ident(base) + ('[' + tail if tail else '')
        body.append(f'  assign {output} = {consume(root, inv)};')
    for nm, root, inv, ci in out_extra:
        for k in range(1, OUT_COPIES[nm]):
            replica = count[ci] - k
            body.append(f'  assign {nm}__c{k} = {root_wire(root, replica, inv)};')
            actual_loads[(root, replica)] += 1
    maximum = max(actual_loads.values(), default=0)
    if maximum > 32:
        raise ValueError(f'internal partition bug: maximum {maximum}')
    lines.extend('  wire ' + w + ';' for w in sorted(wires))
    # Emit the pinned technology inverter explicitly. An RTL unary-not would
    # leave an unmapped $_NOT_ after a standalone synthesis-only check and some
    # lightweight Verilog census parsers treat assign aliases without polarity.
    lines.extend('  (* keep *) INVxp67_ASAP7_75t_R inv_' + dst +
                 ' (.A(' + src[1:] + '), .Y(' + dst + '));'
                 for dst, src in sorted(assignments.items()))
    lines.extend(body)
    lines.append('endmodule')
    for (typ, shape), wrapper in shapes.items():
        lines += ['(* keep_hierarchy *)', 'module ' + wrapper + ' (' + ','.join(ident(pn) for pn, _, _ in shape) + ');']
        for pn, width, direction in shape:
            size = '' if width == 1 else f'[{width-1}:0] '
            lines.append(f'  {"input" if direction == "in" else "output"} wire {size}{ident(pn)};')
        lines.append('  (* keep *) ' + ident(typ) + ' u_cell (' + ','.join(f'.{ident(pn)}({ident(pn)})' for pn, _, _ in shape) + ');')
        lines.append('endmodule')
    dest.write_text('\n'.join(lines) + '\n')
    record = dict(schema='opentallas.kv_group.structural_copy.v1', qualified=False,
                  original_top=oldtop, top=top, source_sha256=actual,
                  parser_sha256=hashlib.sha256(parser.read_bytes()).hexdigest(),
                  generated_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                  fixedpoint_history=history, original_cells=len(live), generated_cells=sum(count.values()),
                  max_terminal_loads=maximum, port_copies={nm: kc for nm, kc in port_copies.values()},
                  allowed_heavy_inputs=sorted(ALLOW_HEAVY), output_copies=OUT_COPIES, copied_cells=manifest,
                  macros=[dict(original=g.cells[ci][1], type=g.cells[ci][0],
                               instance=f'u{ci}_c0.u_cell') for ci in live if kinds[ci] == 'macro'],
                  required_before_gate=['mapped census after re-synthesis', 'source-pinned exact library model',
                                        'sequential equivalence', 'independent arbitrary-init cold-boot/reset convergence'])
    dest.with_suffix('.json').write_text(json.dumps(record, indent=1) + '\n')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--netlist', type=Path, required=True)
    ap.add_argument('--parser', type=Path, required=True)
    ap.add_argument('--sha256', required=True)
    ap.add_argument('--top', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    result = generate(a.netlist, a.parser, a.sha256, a.top, a.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'copied_cells'}, indent=1))


if __name__ == '__main__':
    main()
