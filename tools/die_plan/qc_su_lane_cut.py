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
HEAD_PARAMS = re.compile(r'^(    qfd_dv_lane_h_(?:safe2|su_mem9) #\()([^\n]*?)(\) u_u_head\d+ \()', re.M)


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


def read_extra_head(text, extra, segmented_memory_delay=0):
    """QC-MEM9 11-08: bind the lane head to the memory-transport successor (rtl/physical/qfd_dv_lane_h_su_mem9.sv):
    MEMORY_READ_EXTRA=extra (SU lanes: 9, the parent request 5 + answer 4 of the qc53 plan); same five leaves, same
    pins, no parent change.  extra==0 keeps the original head.  Idempotent."""
    if type(segmented_memory_delay) is not int or segmented_memory_delay not in (0, 1):
        raise ValueError('SEGMENTED_MEMORY_DELAY must be explicit 0 or 1')
    if segmented_memory_delay and not extra:
        raise ValueError('segmented delay requires explicit MEMORY_READ_EXTRA')
    if not extra:
        if re.search(r'\.SEGMENTED_MEMORY_DELAY\(1\)', text):
            raise ValueError('lane head binds a different SEGMENTED_MEMORY_DELAY')
        return text
    if type(extra) is not int or extra < 0:
        raise ValueError('MEMORY_READ_EXTRA must be a nonnegative integer')
    head = re.compile(r'^(    )qfd_dv_lane_h_(?:safe2|su_mem9)( #\()([^\n]*?)(\) u_u_head\d+ \()', re.M)
    def sub(m):
        params = m[3]
        if '.MEMORY_READ_EXTRA(' not in params:
            raise ValueError('lane head has no MEMORY_READ_EXTRA parameter')
        params = re.sub(r'\.MEMORY_READ_EXTRA\(\d+\)', f'.MEMORY_READ_EXTRA({extra})', params)
        flag = re.search(r'\.SEGMENTED_MEMORY_DELAY\((\d+)\)', params)
        if flag and int(flag[1]) != segmented_memory_delay:
            raise ValueError('lane head binds a different SEGMENTED_MEMORY_DELAY')
        if segmented_memory_delay and not flag:
            params += ', .SEGMENTED_MEMORY_DELAY(1)'
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


def _expr_bits(expr, widths):
    """LSB-first bits of bind.py's explicit wiring grammar; reject other RTL."""
    expr = re.sub(r'\s+', '', expr)
    if expr.startswith('{') and expr.endswith('}'):
        parts, depth, start = [], 0, 1
        for i, ch in enumerate(expr[1:-1], 1):
            depth += (ch == '{') - (ch == '}')
            if ch == ',' and depth == 0:
                parts.append(expr[start:i]); start = i + 1
        parts.append(expr[start:-1])
        if any(not x for x in parts):
            raise ValueError('unsupported empty ABI expression')
        return [b for x in reversed(parts) for b in _expr_bits(x, widths)]
    literal = re.fullmatch(r"(\d+)'([bhd])([0-9a-fA-FxXzZ_]+)", expr)
    if literal:
        size, base, value = literal.groups()
        if re.search('[xXzZ]', value):
            raise ValueError('unknown constant in ABI expression')
        number = int(value.replace('_', ''), dict(b=2, h=16, d=10)[base])
        return [('constant', (number >> i) & 1) for i in range(int(size))]
    m = re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?', expr)
    if not m or m[1] not in widths:
        raise ValueError('unsupported or undeclared ABI expression ' + expr)
    name, hi, lo = m.groups()
    hi, lo = (widths[name]-1, 0) if hi is None else (int(hi), int(lo if lo is not None else hi))
    if hi < lo or hi >= widths[name]:
        raise ValueError('out-of-range ABI expression ' + expr)
    return [(name, bit) for bit in range(lo, hi+1)]


def _instances(text):
    pattern = re.compile(r'^    (?P<header>\w+(?: #\([^\n]*\))?) (?P<inst>u_u_(?:exp|rsq|head|rcp|lrly)\d+) \(\n(?P<ports>.*?)^    \);', re.M | re.S)
    out = {}
    for m in pattern.finditer(text):
        ports = {}
        for line in m['ports'].splitlines():
            p = re.fullmatch(r'\s*\.(\w+)\((.*)\),?\s*', line)
            if not p or p[1] in ports:
                raise ValueError('unsupported or duplicate ABI leaf port')
            ports[p[1]] = p[2]
        if m['inst'] in out:
            raise ValueError('duplicate ABI leaf instance')
        out[m['inst']] = (re.sub(r'\s+', '', m['header']), ports)
    return out


def _reference_abi(reference):
    ins, outs = {}, {}
    for name, bit, idx in re.findall(r'^\s*assign (\w+)(?:\[(\d+)\])? = c_i\[(\d+)\];', reference, re.M):
        idx = int(idx)
        if idx in ins:
            raise ValueError('duplicate reference ABI input')
        ins[idx] = (name, int(bit or 0))
    for idx, name, bit in re.findall(r'^\s*assign c_o\[(\d+)\] = (\w+)(?:\[(\d+)\])?;', reference, re.M):
        idx = int(idx)
        if idx in outs:
            raise ValueError('duplicate reference ABI output')
        outs[idx] = (name, int(bit or 0))
    dimensions = re.search(r'input wire \[(\d+):0\] c_i, output wire \[(\d+):0\] c_o', reference)
    if not dimensions or set(ins) != set(range(int(dimensions[1])+1)) or set(outs) != set(range(int(dimensions[2])+1)):
        raise ValueError('incomplete reference ABI assignment census')
    return [ins[k] for k in range(len(ins))], [outs[k] for k in range(len(outs))]


def preserve_input_abi(rtl, frame, report, body, widths, contract, extra, segmented, kv_pipe):
    """Verify all leaf port bits, then retain the pinned master and only rewire c_i."""
    reference = contract['reference_rtl']
    digest = hashlib.sha256(reference.encode()).hexdigest()
    if digest != contract.get('reference_sha256'):
        raise ValueError('reference ABI source hash differs')
    module = re.findall(r'^module (\w+) \(', reference, re.M)
    reference_module = contract.get('reference_module', report['module'])
    if module != [reference_module]:
        raise ValueError('reference ABI module differs')
    if reference_module != report['module'] and contract.get('retarget_module') != report['module']:
        raise ValueError('reference ABI module retarget must be explicit')
    rw = {name: int(hi)+1 if hi else 1 for hi, name in WIRE.findall(reference)}
    rw.update(clk=1, rst_n=1)
    ib, ob = _reference_abi(reference)
    if len(set(ib)) != len(ib):
        raise ValueError('reference ABI repeats an input bit')
    actual_out = [(x['name'], x['bit']) for x in report['outputs']]
    if actual_out != ob:
        raise ValueError('reference ABI output boundary differs')
    ref_body = reference
    if kv_pipe:
        ref_body = kv_wr_pipe_head(ref_body)
    ref_body = read_extra_head(ref_body, extra, segmented)
    if reference_module != report['module']:
        ref_body = re.sub(r'^module '+re.escape(reference_module)+r' \(',
                          'module '+report['module']+' (', ref_body, count=1, flags=re.M)
    expected, actual = _instances(ref_body), _instances(body)
    if set(expected) != set(actual) or len(actual) != 5:
        raise ValueError('reference ABI leaf instance set differs')
    groups = contract.get('aliases', [])
    locations = {(g.get('type'), g.get('partition')) for g in groups}
    if len(locations) > 1:
        raise ValueError('mixed type/partition input ABI aliases')
    if 'source_type' in contract and locations != {(contract['source_type'], contract['source_partition'])}:
        raise ValueError('input ABI source type/partition differs')
    aliases, reverse, sinks = {}, {}, set()
    vectors = vector_names(reference)
    hookups = [f'{n}[{b}]' if rw[n] > 1 or n in vectors else n for n, b in ib]
    for group in groups:
        if group.get('module') != reference_module or group.get('reference_sha256') != digest:
            raise ValueError('alias group reference differs')
        if not group.get('r8_member_id'):
            raise ValueError('alias has no exact R8 member')
        leaf = group['sink_leaf'].replace('u_', 'u_u_', 1)
        port = group['sink_port']
        if leaf not in expected or port not in expected[leaf][1] or port not in actual[leaf][1]:
            raise ValueError('alias sink does not exist')
        rb = _expr_bits(expected[leaf][1][port], rw)
        ab = _expr_bits(actual[leaf][1][port], widths)
        for item in group['bits']:
            idx, sink_bit = item['abi_bit'], item['sink_bit']
            original = (item['original_local']['name'], item['original_local']['bit'])
            if type(idx) is not int or idx < 0 or idx >= len(ib) or ib[idx] != original:
                raise ValueError('alias ABI bit or original local differs')
            if idx in aliases or (leaf, port, sink_bit) in sinks:
                raise ValueError('duplicate ABI alias bit or sink')
            if _expr_bits(item['original_frame_expr'], rw) != [original]:
                raise ValueError('alias original frame expression differs')
            replacement = _expr_bits(item['replacement_frame_expr'], widths)
            if len(replacement) != 1 or replacement[0][0] == 'constant':
                raise ValueError('alias replacement must be one actual net bit')
            if sink_bit < 0 or sink_bit >= len(rb) or sink_bit >= len(ab) or rb[sink_bit] != original or ab[sink_bit] != replacement[0]:
                raise ValueError('alias sink bit does not match exact wiring')
            if replacement[0] in reverse and reverse[replacement[0]] != original:
                raise ValueError('alias replacement merges different ABI bits')
            if replacement[0] == original:
                raise ValueError('unchanged input must not have a changed-input alias')
            aliases[idx] = replacement[0]
            reverse[replacement[0]] = original
            sinks.add((leaf, port, sink_bit))
            hookups[idx] = item['replacement_frame_expr']
    # This comparison covers every port, including unchanged inputs, outputs,
    # internal connections, constants, clock and the exact delivered reset.
    for leaf in expected:
        eh, ep = expected[leaf]; ah, ap = actual[leaf]
        if eh != ah or set(ep) != set(ap):
            raise ValueError('reference ABI leaf module/parameters/ports differ')
        for port in ep:
            eb = _expr_bits(ep[port], rw)
            ab = _expr_bits(ap[port], widths)
            ab = [('rst_n', 0) if x == (report['reset_source'], 0) else reverse.get(x, x) for x in ab]
            if eb != ab:
                raise ValueError(f'reference ABI leaf port differs: {leaf}.{port}')
    for idx, (name, bit) in enumerate(ib):
        if idx not in aliases and _expr_bits(hookups[idx], widths) != [(name, bit)]:
            raise ValueError('unchanged reference ABI input is unavailable')
    output_exprs = [f'{n}[{b}]' if rw[n] > 1 or n in vectors else n for n, b in ob]
    c_i = '{' + ', '.join(reversed(hookups)) + '}'
    c_o = '{' + ', '.join(reversed(output_exprs)) + '}'
    pattern = re.compile(r'^    '+re.escape(report['module'])+r' u_lane'+str(report['lane'])+r' \([^\n]*\);', re.M)
    replacement = f"    {report['module']} u_lane{report['lane']} (.clk(clk), .rst_n({report['reset_source']}), .c_i({c_i}), .c_o({c_o}));"
    frame, count = pattern.subn(lambda _: replacement, frame)
    if count != 1:
        raise ValueError('expected one generated group hookup')
    report.update(inputs=[dict(name=n, bit=b) for n,b in ib], input_bits=len(ib),
                  input_abi_reference_sha256=digest, input_abi_changed_bits=len(aliases),
                  input_abi_all_leaf_ports_verified=True)
    return ref_body, frame, report


def cut(source, lane, module=None, memory_alignment=None, kv_wr_pipe=0, memory_read_extra=0,
        segmented_memory_delay=0, input_abi=None):
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
    body = read_extra_head(body, memory_read_extra, segmented_memory_delay)
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
    if segmented_memory_delay:
        report['segmented_memory_delay'] = segmented_memory_delay
    if input_abi is not None:
        return preserve_input_abi(rtl, frame, report, body, widths, input_abi,
                                  memory_read_extra, segmented_memory_delay, kv_wr_pipe)
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
    p.add_argument('--memory-read-extra', type=int, default=0)
    p.add_argument('--segmented-memory-delay', type=int, choices=(0, 1), default=0)
    p.add_argument('--input-abi', type=Path, help='explicit pinned reference + changed input aliases JSON')
    a = p.parse_args()
    abi = json.loads(a.input_abi.read_text()) if a.input_abi else None
    if abi is not None:
        reference = Path(abi['reference_rtl'])
        if not reference.is_absolute():
            reference = a.input_abi.parent / reference
        abi['reference_rtl'] = reference.read_text()
    rtl, frame, report = cut(a.source.read_text(), a.lane, a.module, a.memory_alignment,
                             a.kv_wr_pipe, a.memory_read_extra, a.segmented_memory_delay, abi)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / (report['module'] + '.sv')).write_text(rtl)
    (a.out / 'frame.sv').write_text(frame)
    (a.out / 'cut.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('module', 'input_bits', 'output_bits', 'added_cycles')}))


if __name__ == '__main__':
    main()
