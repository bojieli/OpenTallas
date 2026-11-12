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
HEAD_PARAMS = re.compile(r'^(    qfd_dv_lane_h_safe2 #\()([^\n]*?)(\) u_u_head\d+ \()', re.M)


def kv_wr_pipe_head(text):
    """DIE-QC-58 10-31: bind the lane head's KV_WR_PIPE=1 (qfd_dv_head_safe1.sv: fp8r split over the lane kv_wdata
    flop and the head's existing kv_wdata out flop; same function (SAT-proved), zero added cycles).  Idempotent."""
    def sub(m):
        if '.KV_WR_PIPE(' in m[2]:
            if '.KV_WR_PIPE(1)' not in m[2]:
                raise ValueError('lane head binds a different KV_WR_PIPE')
            return m[0]
        return m[1] + m[2] + ', .KV_WR_PIPE(1)' + m[3]
    out, n = HEAD_PARAMS.subn(sub, text)
    if n != 1:
        raise ValueError(f'expected exactly one parameterized qfd_dv_lane_h_safe2 lane head, found {n}')
    return out


def read_extra_head(text, extra):
    """QC-MEM9 11-08: bind the lane head to the memory-transport successor (rtl/physical/qfd_dv_lane_h_su_mem9.sv):
    MEMORY_READ_EXTRA=extra (SU lanes: 9, the parent request 5 + answer 4 of the qc53 plan); same five leaves, same
    pins, no parent change.  extra==0 keeps the original head.  Idempotent."""
    if not extra:
        return text
    head = re.compile(r'^(    )qfd_dv_lane_h_(?:safe2|su_mem9)( #\()([^\n]*?)(\) u_u_head\d+ \()', re.M)
    def sub(m):
        params = m[3]
        if '.MEMORY_READ_EXTRA(' not in params:
            raise ValueError('lane head has no MEMORY_READ_EXTRA parameter')
        params = re.sub(r'\.MEMORY_READ_EXTRA\(\d+\)', f'.MEMORY_READ_EXTRA({extra})', params)
        return f'{m[1]}qfd_dv_lane_h_su_mem9{m[2]}{params}{m[4]}'
    out, n = head.subn(sub, text)
    if n != 1:
        raise ValueError(f'expected exactly one lane head for READ_EXTRA, found {n}')
    return out


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


def concat(bits, vectors=()):
    return '{' + ', '.join(f'{n}[{b}]' if w > 1 or n in vectors else n for n, b, w in reversed(bits)) + '}'


def vector_names(source):
    """Names the bound source declares with a range, including one-bit [0:0] vectors: the cut keeps that range so
    every n[0] select copied from the leaf bodies stays legal (QC-VERIFY-GAPS: 'wire n;' + n[0] = Verilator error)."""
    return {name for hi, name in WIRE.findall(source) if hi}


def cut(source, lane, module=None, memory_alignment=None, kv_wr_pipe=0, memory_read_extra=0):
    module = module or f'qfd_qc_su_lane_w_l{lane}'
    if len(re.findall(r'\bendmodule\b', source)) != 1:
        raise ValueError('expected one bound partition module')
    widths = {name: int(hi) + 1 if hi else 1 for hi, name in WIRE.findall(source)}
    vectors = vector_names(source)
    # bind.py scalar clock/reset inputs need not have local wire declarations.
    widths.update(clk=1, rst_n=1)
    all_leaves = list(LEAF.finditer(source))
    chosen = [m for m in all_leaves if int(m['lane']) == lane]
    if {m['kind'] for m in chosen} != KINDS or len(chosen) != 5:
        raise ValueError(f'lane {lane}: expected exactly five as-built leaves, found {[m["kind"] for m in chosen]}')
    head = next(m for m in chosen if m['kind'] == 'head')
    alignment = re.search(r'\.MEMORY_ALIGNMENT\((\d+)\)', head['body'])
    alignment = int(alignment[1]) if alignment else None
    if memory_alignment is not None and alignment != memory_alignment:
        raise ValueError(f'lane {lane}: bound MEMORY_ALIGNMENT={alignment}, required {memory_alignment}; regenerate the canonical bind')
    body = '\n'.join(m['body'] for m in chosen)
    if kv_wr_pipe:
        body = kv_wr_pipe_head(body)
    body = read_extra_head(body, memory_read_extra)
    reset_args=re.findall(r'\.rst_n\(([^()]+)\)',body)
    if len(reset_args)!=5 or len(set(reset_args))!=1 or not re.fullmatch(r'rst_n(?:_t\d+)?',reset_args[0]):
        raise ValueError('five-leaf group requires one exact delivered reset net')
    reset_source=reset_args[0]
    selected = refs(body, widths)
    remainder = source
    for m in reversed(chosen):
        remainder = remainder[:m.start()] + remainder[m.end():]
    # Declarations are not uses. This census is of actual instance/assign references.
    outside = refs(WIRE.sub('', remainder), widths)
    owned = {n for n in selected if re.match(rf'w_u_(?:exp|rsq|head|rcp|lrly){lane}_', n)}
    inputs = {n: bits for n, bits in selected.items() if n not in owned and n not in ('clk', 'rst_n', reset_source)}
    outputs = {n: selected[n] & outside.get(n, set()) for n in owned}
    outputs = {n: bits for n, bits in outputs.items() if bits}
    def ordered(mapping):
        return [(n, b, widths[n]) for n in sorted(mapping) for b in sorted(mapping[n])]
    ib, ob = ordered(inputs), ordered(outputs)
    decls = ['    wire ' + (f'[{widths[n]-1}:0] ' if widths[n] > 1 or n in vectors else '') + n + ';'
             for n in sorted(selected) if n not in ('clk', 'rst_n', reset_source)]
    # The bit assignments are wiring only, and never tie an unused bit or add a register.
    assigns = [f'    assign {n}[{b}] = c_i[{i}];' if w > 1 or n in vectors else f'    assign {n} = c_i[{i}];'
               for i, (n, b, w) in enumerate(ib)]
    assigns += [f'    assign c_o[{i}] = {n}[{b}];' if w > 1 or n in vectors else f'    assign c_o[{i}] = {n};'
                for i, (n, b, w) in enumerate(ob)]
    rtl = '\n'.join(['// Generated exact grouping of five bind.py leaves; zero added cycles.', '`default_nettype none',
                     f'module {module} (input wire clk, input wire rst_n,',
                     f'    input wire [{len(ib)-1}:0] c_i, output wire [{len(ob)-1}:0] c_o);',
                     *decls, *assigns, re.sub(r'\b'+re.escape(reset_source)+r'\b','rst_n',body), 'endmodule', '`default_nettype wire', ''])
    replacement = f'    {module} u_lane{lane} (.clk(clk), .rst_n({reset_source}), .c_i({concat(ib, vectors)}), .c_o({concat(ob, vectors)}));\n'
    frame = remainder.replace('endmodule', replacement + 'endmodule')
    # Remove only wires fully private to the cut; external wires retain their original declaration.
    private = owned - outputs.keys()
    frame = WIRE.sub(lambda m: '' if m[2] in private else m[0], frame)
    report = dict(schema='opentallas.qc_su_lane_cut.v1', lane=lane, module=module,
                  source_sha256=hashlib.sha256(source.encode()).hexdigest(), added_cycles=0,
                  memory_alignment=alignment, kv_wr_pipe=int(bool(kv_wr_pipe)), memory_read_extra=int(memory_read_extra), reset_source=reset_source,
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
    p.add_argument('--memory-alignment', type=int, help='fail closed unless the bound lane head has this exact parameter (production QCL contract:3)')
    p.add_argument('--kv-wr-pipe', type=int, default=0, choices=(0, 1),
                   help='bind the lane head KV_WR_PIPE (fp8r split over the existing kv_wdata flops, zero added cycles)')
    a = p.parse_args()
    rtl, frame, report = cut(a.source.read_text(), a.lane, a.module, a.memory_alignment, a.kv_wr_pipe)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / (report['module'] + '.sv')).write_text(rtl)
    (a.out / 'frame.sv').write_text(frame)
    (a.out / 'cut.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('module', 'input_bits', 'output_bits', 'added_cycles')}))


if __name__ == '__main__':
    main()
