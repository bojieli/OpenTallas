#!/usr/bin/env python3
"""Zero-delay, Verilator-friendly simulation models of standard cells generated from their Liberty files
(anim-1011 gate-level replay).  The PDK's own Verilog models (UDPs, specify blocks, delayed_* notifier nets) do not
build under Verilator; Yosys' read_liberty rejects statetable cells (ASAP7 ICGs).  This script reads, per cell:
  pin direction + function            -> continuous assign
  ff (IQ, IQN) {clocked_on, next_state, clear, preset, clear_preset_var1/2}  -> always @(edge) with async clear/preset
  latch (IQ, IQN) {enable, data_in, clear, preset}                         -> level-sensitive always
  clock_gating_integrated_cell "latch_posedge|latch_negedge[_precontrol|_postcontrol]" -> enable latch + AND/OR gate
A cell with no function on any output (fillers, taps, decaps, antenna) becomes an empty module.

    python3 lib2v.py --out cells.v lib1.lib[.gz] lib2 ...
Every module carries /*verilator tracing_off*/ so a netlist trace holds the netlist's own nets, not cell internals.
"""
import argparse, gzip, re, sys

TOK = re.compile(r'\s*(?:(/\*.*?\*/)|("(?:[^"\\]|\\.)*")|([{}();:,])|([^\s{}();:,"]+))', re.S)


def tokens(text):
    text = text.replace('\\\n', ' ')
    for m in TOK.finditer(text):
        if m.group(1): continue
        yield m.group(2) or m.group(3) or m.group(4)


def parse(text):
    """liberty -> nested dict nodes {type, args, attrs{}, groups[]} (only what the models need is kept)"""
    toks = list(tokens(text)); i = 0
    root = dict(type='root', args=[], attrs={}, groups=[]); stack = [root]
    n = len(toks)
    while i < n:
        t = toks[i]
        if t == '}':
            stack.pop(); i += 1; continue
        if i + 1 < n and toks[i + 1] == ':':   # simple attribute
            v = toks[i + 2] if i + 2 < n else ''
            stack[-1]['attrs'][t] = v.strip('"')
            i += 3
            if i < n and toks[i] == ';': i += 1
            continue
        if i + 1 < n and toks[i + 1] == '(':   # group or complex attribute
            j = i + 2; args = []
            while j < n and toks[j] != ')':
                if toks[j] != ',': args.append(toks[j].strip('"'))
                j += 1
            j += 1
            if j < n and toks[j] == '{':
                g = dict(type=t, args=args, attrs={}, groups=[])
                stack[-1]['groups'].append(g); stack.append(g); i = j + 1
            else:
                if j < n and toks[j] == ';': j += 1
                i = j
            continue
        i += 1
    return root


def lib_cells(path):
    data = gzip.open(path, 'rt').read() if path.endswith('.gz') else open(path).read()
    # drop timing / power / internal tables before parsing (they are most of the file)
    data = re.sub(r'\b(timing|internal_power|leakage_power|receiver_capacitance|output_current_rise|output_current_fall)\s*\(', r'\1_SKIP(', data)
    root = parse(data)
    lib = root['groups'][0] if root['groups'] else root
    return [g for g in lib['groups'] if g['type'] == 'cell']


FN_TOK = re.compile(r"\s*([A-Za-z_][\w\[\]]*|[01]|[!~&|^*+()']|\s)")


def fexpr(f, rename=None):
    """liberty boolean function -> Verilog expression ('!' / postfix \"'\" not, '*' / '&' / juxtaposition and, '+' / '|' or, '^' xor)"""
    rename = rename or {}
    toks = [t for t in re.findall(r"[A-Za-z_][\w\[\]]*|[01]|[!&|^*+()']", f)]
    out = []; prev_operand = False
    for t in toks:
        if t == "'":
            # postfix not on the previous operand / parenthesised group
            if out and out[-1] == ')':
                depth = 0
                for k in range(len(out) - 1, -1, -1):
                    if out[k] == ')': depth += 1
                    elif out[k] == '(':
                        depth -= 1
                        if depth == 0: out.insert(k, '~'); break
            else:
                out.insert(len(out) - 1, '~')
            continue
        is_operand = t not in ('!', '&', '|', '^', '*', '+', ')', '(') or t == '('
        if prev_operand and (t == '(' or t == '!' or t not in ('&', '|', '^', '*', '+', ')')):
            out.append('&')   # juxtaposition = AND
        if t == '!': out.append('~'); prev_operand = False; continue
        if t in ('*', '&'): out.append('&'); prev_operand = False; continue
        if t in ('+', '|'): out.append('|'); prev_operand = False; continue
        if t == '^': out.append('^'); prev_operand = False; continue
        if t == '(': out.append('('); prev_operand = False; continue
        if t == ')': out.append(')'); prev_operand = True; continue
        out.append("1'b1" if t == '1' else "1'b0" if t == '0' else rename.get(t, t)); prev_operand = True
    return ' '.join(out) if out else "1'b0"


def model(cell):
    name = cell['args'][0]
    pins = [g for g in cell['groups'] if g['type'] == 'pin']
    buses = [g for g in cell['groups'] if g['type'] == 'bus']
    if buses: return None
    ins = [p['args'][0] for p in pins if p['attrs'].get('direction') == 'input']
    outs = [p for p in pins if p['attrs'].get('direction') in ('output', 'inout')]
    ports = [p['args'][0] for p in pins if p['attrs'].get('direction') in ('input', 'output', 'inout')]
    L = ['/*verilator tracing_off*/', 'module %s (%s);' % (name, ', '.join(ports))]
    for p in ins: L.append('  input %s;' % p)
    for p in outs: L.append('  output %s;' % p['args'][0])
    seq = [g for g in cell['groups'] if g['type'] in ('ff', 'latch')]
    icg = cell['attrs'].get('clock_gating_integrated_cell')
    kind = 'comb'
    if icg:
        kind = 'icg'
        ck = next((p['args'][0] for p in pins if p['attrs'].get('clock_gate_clock_pin') == 'true'), 'CLK')
        en = [p['args'][0] for p in pins if p['attrs'].get('clock_gate_enable_pin') == 'true' or p['attrs'].get('clock_gate_test_pin') == 'true']
        go = next((p['args'][0] for p in outs if p['attrs'].get('clock_gate_out_pin') == 'true'), outs[0]['args'][0] if outs else None)
        ena = ' | '.join(en) if en else "1'b1"
        if icg.startswith('latch_posedge'):
            L += ['  reg en_l;', '  always @* if (!%s) en_l = %s;' % (ck, ena), '  assign %s = %s & en_l;' % (go, ck)]
        elif icg.startswith('latch_negedge'):
            L += ['  reg en_l;', '  always @* if (%s) en_l = %s;' % (ck, ena), '  assign %s = %s | ~en_l;' % (go, ck)]
        else:
            return None
        for p in outs:
            if p['args'][0] != go and p['attrs'].get('function'):
                L.append('  assign %s = %s;' % (p['args'][0], fexpr(p['attrs']['function'])))
    elif seq:
        g = seq[0]; kind = g['type']
        iq, iqn = (g['args'] + ['IQ', 'IQN'])[:2]
        a = g['attrs']
        ns0 = (a.get('next_state') or a.get('data_in') or '').replace(' ', '')
        inv0 = ns0.startswith('!') or ns0.endswith("'")
        # power-up: logical Q = 0, as the RTL simulation's zero-initialised registers
        L += ['  reg %s = 1\'b%d;' % (iq, 1 if inv0 else 0), '  wire %s = ~%s;' % (iqn, iq)]
        clr = fexpr(a['clear']) if a.get('clear') else None
        pre = fexpr(a['preset']) if a.get('preset') else None
        if g['type'] == 'ff':
            ck = a.get('clocked_on', 'CLK').strip()
            neg = ck.startswith('!') or ck.endswith("'")
            ckn = ck.strip("!'() ")
            L.append('  wire ot_d = %s;' % fexpr(a.get('next_state', '0')))
            sens = ['%s %s' % ('negedge' if neg else 'posedge', ckn)]
            if clr: L.append('  wire ot_clr = %s;' % clr); sens.append('posedge ot_clr')
            if pre: L.append('  wire ot_pre = %s;' % pre); sens.append('posedge ot_pre')
            body = []
            if clr and pre: body = ['if (ot_clr) %s <= 1\'b0; else if (ot_pre) %s <= 1\'b1; else %s <= ot_d;' % (iq, iq, iq)]
            elif clr: body = ['if (ot_clr) %s <= 1\'b0; else %s <= ot_d;' % (iq, iq)]
            elif pre: body = ['if (ot_pre) %s <= 1\'b1; else %s <= ot_d;' % (iq, iq)]
            else: body = ['%s <= ot_d;' % iq]
            L.append('  always @(%s) %s' % (' or '.join(sens), body[0]))
        else:
            L.append('  always @* begin')
            if clr: L.append('    if (%s) %s = 1\'b0; else' % (clr, iq))
            if pre: L.append('    if (%s) %s = 1\'b1; else' % (pre, iq))
            L.append('    if (%s) %s = %s;' % (fexpr(a.get('enable', '0')), iq, fexpr(a.get('data_in', '0'))))
            L.append('  end')
        for p in outs:
            f = p['attrs'].get('function')
            if f: L.append('  assign %s = %s;' % (p['args'][0], fexpr(f)))
    else:
        any_fn = False
        for p in outs:
            f = p['attrs'].get('function')
            if f: L.append('  assign %s = %s;' % (p['args'][0], fexpr(f))); any_fn = True
        if outs and not any_fn: kind = 'nofunc'
        if not outs: kind = 'physical'
    L.append('endmodule')
    info = dict(kind=kind)
    if seq:
        g = seq[0]; a = g['attrs']
        ns = (a.get('next_state') or a.get('data_in') or '').replace(' ', '')
        info.update(state=(g['args'] + ['IQ'])[0], inv=ns.startswith('!') or ns.endswith("'"))
    if icg: info.update(state='en_l', inv=False)
    return name, info, '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True); ap.add_argument('--kinds'); ap.add_argument('libs', nargs='+')
    a = ap.parse_args()
    seen = {}; text = ['// GENERATED by tools/explorer_elem/lib2v.py from: ' + ' '.join(x.rsplit('/', 1)[-1] for x in a.libs),
                       '// verilator lint_off UNOPTFLAT', '// verilator lint_off LATCH', '// verilator lint_off COMBDLY', '// verilator lint_off MULTIDRIVEN']
    for lp in a.libs:
        for c in lib_cells(lp):
            m = model(c)
            if not m or m[0] in seen: continue
            seen[m[0]] = m[1]; text.append(m[2])
    open(a.out, 'w').write('\n'.join(text) + '\n')
    if a.kinds:
        import json; open(a.kinds, 'w').write(json.dumps(seen))
    import collections
    print('lib2v: %d cells %s' % (len(seen), dict(collections.Counter(v['kind'] for v in seen.values()))))


if __name__ == '__main__':
    main()
