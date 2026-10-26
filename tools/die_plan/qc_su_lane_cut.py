#!/usr/bin/env python3
"""Group the five as-built SU leaves without changing a register or a cycle.

Input is bind.py's emitted partition RTL, not a hand-written SU facsimile.
The returned frame instantiates the extracted lane at the same named nets.
Ports include only bits actually crossing the cut; provisional plan bus counts
are deliberately not used. The emitter rejects unsupported generated syntax.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

WIRE = re.compile(r'^\s*wire\s+(?:\[(\d+):0\]\s+)?(\w+)\s*;', re.M)
REF = re.compile(r'\b([A-Za-z_]\w*)(?:\[(\d+)(?::(\d+))?\])?')
LEAF = re.compile(r'^    // as-built [^\n]+\n(?P<body>    (?P<module>\w+)(?: #\([^\n]*\))? (?P<inst>u_u_(?P<kind>exp|rsq|head|rcp|lrly)(?P<lane>\d+)) \(\n.*?^    \);)', re.M | re.S)
KINDS = {'exp', 'rsq', 'head', 'rcp', 'lrly'}


def refs(text, widths):
    result = collections.defaultdict(set)
    for m in REF.finditer(text):
        name, hi, lo = m.groups()
        if name not in widths:
            continue
        if hi is None:
            bits = range(widths[name])
        else:
            hi, lo = int(hi), int(lo if lo is not None else hi)
            if hi < lo or hi >= widths[name]:
                raise ValueError(f'out-of-range bound reference {m.group(0)}')
            bits = range(lo, hi + 1)
        result[name].update(bits)
    return result


def concat(bits):
    return '{' + ', '.join(f'{n}[{b}]' if w > 1 else n for n, b, w in reversed(bits)) + '}'


def cut(source, lane, module=None):
    module = module or f'qfd_qc_su_lane_w_l{lane}'
    if len(re.findall(r'\bendmodule\b', source)) != 1:
        raise ValueError('expected one bound partition module')
    widths = {name: int(hi) + 1 if hi else 1 for hi, name in WIRE.findall(source)}
    # bind.py scalar clock/reset inputs need not have local wire declarations.
    widths.update(clk=1, rst_n=1)
    all_leaves = list(LEAF.finditer(source))
    chosen = [m for m in all_leaves if int(m['lane']) == lane]
    if {m['kind'] for m in chosen} != KINDS or len(chosen) != 5:
        raise ValueError(f'lane {lane}: expected exactly five as-built leaves, found {[m["kind"] for m in chosen]}')
    body = '\n'.join(m['body'] for m in chosen)
    selected = refs(body, widths)
    remainder = source
    for m in reversed(chosen):
        remainder = remainder[:m.start()] + remainder[m.end():]
    # Declarations are not uses. This census is of actual instance/assign references.
    outside = refs(WIRE.sub('', remainder), widths)
    owned = {n for n in selected if re.match(rf'w_u_(?:exp|rsq|head|rcp|lrly){lane}_', n)}
    inputs = {n: bits for n, bits in selected.items() if n not in owned and n not in ('clk', 'rst_n')}
    outputs = {n: selected[n] & outside.get(n, set()) for n in owned}
    outputs = {n: bits for n, bits in outputs.items() if bits}
    def ordered(mapping):
        return [(n, b, widths[n]) for n in sorted(mapping) for b in sorted(mapping[n])]
    ib, ob = ordered(inputs), ordered(outputs)
    decls = ['    wire ' + (f'[{widths[n]-1}:0] ' if widths[n] > 1 else '') + n + ';'
             for n in sorted(selected) if n not in ('clk', 'rst_n')]
    # The bit assignments are wiring only, and never tie an unused bit or add a register.
    assigns = [f'    assign {n}[{b}] = c_i[{i}];' if w > 1 else f'    assign {n} = c_i[{i}];'
               for i, (n, b, w) in enumerate(ib)]
    assigns += [f'    assign c_o[{i}] = {n}[{b}];' if w > 1 else f'    assign c_o[{i}] = {n};'
                for i, (n, b, w) in enumerate(ob)]
    rtl = '\n'.join(['// Generated exact grouping of five bind.py leaves; zero added cycles.', '`default_nettype none',
                     f'module {module} (input wire clk, input wire rst_n,',
                     f'    input wire [{len(ib)-1}:0] c_i, output wire [{len(ob)-1}:0] c_o);',
                     *decls, *assigns, body, 'endmodule', '`default_nettype wire', ''])
    replacement = f'    {module} u_lane{lane} (.clk(clk), .rst_n(rst_n), .c_i({concat(ib)}), .c_o({concat(ob)}));\n'
    frame = remainder.replace('endmodule', replacement + 'endmodule')
    # Remove only wires fully private to the cut; external wires retain their original declaration.
    private = owned - outputs.keys()
    frame = WIRE.sub(lambda m: '' if m[2] in private else m[0], frame)
    report = dict(schema='opentallas.qc_su_lane_cut.v1', lane=lane, module=module,
                  source_sha256=hashlib.sha256(source.encode()).hexdigest(), added_cycles=0,
                  leaves=[dict(instance=m['inst'], module=m['module']) for m in chosen],
                  inputs=[dict(name=n, bit=b) for n,b,_ in ib],
                  outputs=[dict(name=n, bit=b) for n,b,_ in ob],
                  input_bits=len(ib), output_bits=len(ob),
                  boundary='Raw exact cut; dedicated face-register and placement gates still required.')
    return rtl, frame, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--lane', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--module')
    a = p.parse_args()
    rtl, frame, report = cut(a.source.read_text(), a.lane, a.module)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / (report['module'] + '.sv')).write_text(rtl)
    (a.out / 'frame.sv').write_text(frame)
    (a.out / 'cut.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('module', 'input_bits', 'output_bits', 'added_cycles')}))


if __name__ == '__main__':
    main()
