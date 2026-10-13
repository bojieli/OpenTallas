#!/usr/bin/env python3
"""Slot cells of the Qwen ROM TP8 die (contract slots whose bundles are WIDTH-ONLY aggregates): ONE packing table per
master -> wrapper RTL (module named as the master), body-shaped bench shim, JSON table.

    gen_slot.py MASTER [--check]        (run from the repo root; tables in physical/qwen_kv_slots/slot_tables.py)

Table fields are LSB-FIRST.  A field is
    'port'             the whole body port
    ('port', lo, w)    bits [lo +: w] of a body port
    (None, w)          contract bits with NO body port: reported, never tied off, NOT pins of the cell (always the top
                       bits of the bundle, so the cell port is the bound low part [bound-1:0])
    ('!port', 1)       a credit / ready bit that runs AGAINST the bundle's flow: its own 1-bit port <bundle>_cr
An output port may appear in several bundles (wire copies of one body output register set).  `extra` lists body ports
with no contract bundle as extra cell pins (slot_change_request), `tie` ties retired body inputs to a constant (with
the reason), `open` names body outputs that are not pins of the cell (observed by the bench through the hierarchy)."""
import importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def body_ports(path, module, env):
    src = open(path).read()
    m = re.search(r'^module\s+' + module + r'\b', src, re.M)
    hdr = src[m.start():]
    hdr = hdr[:re.search(r'^\s*\);', hdr, re.M).start()]
    hdr = hdr[hdr.rindex(') (') + 3:] if ') (' in hdr else hdr[hdr.index('(') + 1:]
    hdr = re.sub(r'//[^\n]*', '', hdr)
    P = {}; d = w = None
    for tok in hdr.split(','):
        t = tok.strip()
        if not t: continue
        r = re.match(r'(input|output)\s+(?:wire\s+|reg\s+)?(\[[^\]]+\])?\s*(\w+)$', t)
        if r:
            d = r.group(1); wtxt = r.group(2); n = r.group(3)
            if wtxt:
                hi = wtxt[1:wtxt.rindex(':')].replace('$clog2', 'clog2')
                w = int(eval(hi, dict(env, clog2=lambda x: (int(x) - 1).bit_length()))) + 1
            else:
                w = 1
        else:
            assert re.match(r'\w+$', t), (module, t)
            n = t
        P[n] = (d, w)
    return P


def build(M):
    P = body_ports(M['body_file'], M['body'], M.get('env', {}))
    clk, rst = M.get('clock', 'clk'), M.get('reset', 'rst_n')
    used = {}; rows = []
    for name, cw, flow, peer, fl in M['bundles']:
        lsb = 0; fields = []
        for f in fl:
            against = False; lo = None
            if isinstance(f, tuple) and f[0] is None:
                fields.append(dict(port=None, lsb=lsb, width=f[1])); lsb += f[1]; continue
            if isinstance(f, tuple) and f[0].startswith('!'):
                n, against, w = f[0][1:], True, 1
            elif isinstance(f, tuple):
                n, lo, w = f
            else:
                n, w = f, P[f][1]
            d, pw = P[n]
            if lo is None and not against: assert w == pw
            assert (lo or 0) + w <= pw, (name, n)
            assert (d == 'output') == ((flow == 'out') != against), (name, n, d)
            key = (n, lo or 0, w)
            for (n2, lo2, w2), b2 in used.items():
                if n2 == n and not (lo2 + w2 <= (lo or 0) or (lo or 0) + w <= lo2):
                    assert d == 'output', ('input bits bound twice', name, n)
            used[key] = name
            fields.append(dict(port=n, plo=lo or 0, lsb=lsb, width=w, dir='in' if d == 'input' else 'out',
                               against_flow=against)); lsb += w
        assert lsb == cw, (name, lsb, cw)
        seen_unb = False
        for f in fields:
            if f['port'] is None: seen_unb = True
            else: assert not seen_unb or f['against_flow'], ('unbound bits must be the top of the bundle', name)
        rows.append(dict(bundle=name, width=cw, flow=flow, peer=peer, fields=fields))
    # coverage of the body ports
    cov = {n: [0] * w for n, (d, w) in P.items()}
    for (n, lo, w) in used:
        for i in range(lo, lo + w): cov[n][i] += 1
    extra = M.get('extra', {}); tie = M.get('tie', {}); opn = M.get('open', [])
    for n in list(extra) + list(tie) + list(opn) + [clk]:
        assert n in P, n
        assert not any(cov[n]), ('also in a bundle', n)
        cov[n] = [1] * len(cov[n])
    miss = [n for n, c in cov.items() if not all(c)]
    assert not miss, ('body ports with no binding', miss)
    return P, rows


def cell_ports(M, P, rows):
    """(port, dir, width, [fields]) of the cell: per bundle the bound bits [bound-1:0]; _d / _cr for credit bundles"""
    out = []
    for r in rows:
        main = [f for f in r['fields'] if f['port'] and not f['against_flow']]
        ag = [f for f in r['fields'] if f['port'] and f['against_flow']]
        if main:
            hi = max(f['lsb'] + f['width'] for f in main)
            out.append((r['bundle'] + ('_d' if ag else ''), r['flow'], hi, main))
        for f in ag:
            out.append((r['bundle'] + '_cr', 'in' if r['flow'] == 'out' else 'out', 1, [dict(f, lsb=0)]))
    for n, pin in M.get('extra', {}).items():
        d, w = P[n]
        out.append((pin, 'in' if d == 'input' else 'out', w, [dict(port=n, plo=0, lsb=0, width=w)]))
    return out


def bsl(n, w, lo, wd):
    return n if (w == 1 and wd == 1) else (f'{n}[{lo}]' if wd == 1 else f'{n}[{lo + wd - 1}:{lo}]')


def main():
    name = sys.argv[1]
    spec = importlib.util.spec_from_file_location('slot_tables', os.path.join(HERE, 'slot_tables.py'))
    T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
    M = T.MASTERS[name]
    P, rows = build(M); cp = cell_ports(M, P, rows)
    clk, rst = M.get('clock', 'clk'), M.get('reset', 'rst_n')
    unb = [dict(bundle=r['bundle'], bits=[f['lsb'] + f['width'] - 1, f['lsb']], flow=r['flow'], peer=r['peer'])
           for r in rows for f in r['fields'] if f['port'] is None]
    nbits = sum(w for _, _, w, _ in cp)
    if '--check' in sys.argv:
        print('OK', name, len(rows), 'bundles', sum(r['width'] for r in rows), 'contract bits', nbits, 'cell pin bits',
              len(unb), 'unbound ranges'); return
    jp = f'physical/qwen_kv_slots/{name}_pack.json'
    json.dump(dict(cell=name, body=M['body'], body_file=M['body_file'], order='LSB-first', clock=f'ck -> {clk}',
                   bundles=rows, unbound=unb, extra_pins=M.get('extra', {}), tied=M.get('tie', {}),
                   not_pins=M.get('open', []), notes=M.get('notes', ''),
                   cell_ports=[dict(port=n, dir=d, width=w) for n, d, w, _ in cp]), open(jp, 'w'), indent=1)
    MUT = 'OT_' + name.upper() + '_SLOT_MUT'
    mb = M['mutant']                      # an output bundle whose bits 0 / 1 are swapped by the bench mutant
    L = [f'// GENERATED by physical/qwen_kv_slots/gen_slot.py {name} from slot_tables.py ({name}_pack.json): do not edit.',
         f'// Qwen ROM TP8 slot cell {name}: WIRING ONLY around the body {M["body"]}.'] + \
        ['// ' + l for l in M.get('notes', '').splitlines()] + \
        [f'// {MUT} (bench mutant only): {mb} bits 0 and 1 swapped.', f'module {name} (', '    input  wire ck,']
    rsi = [n for n, d, w, fs in cp if any(f['port'] == rst for f in fs)]
    pl = [f"    {'input ' if d == 'in' else 'output'} wire {f'[{w - 1}:0] ' if w > 1 else ''}{n}" for n, d, w, _ in cp]
    L += [',\n'.join(pl), ');']
    conn = {clk: 'ck'}; body = []
    # one internal wire per body port, then the bundle assigns
    for n, (d, w) in P.items():
        if n == clk: continue
        body.append(f"    wire {f'[{w - 1}:0] ' if w > 1 else ''}w_{n};")
        conn[n] = 'w_' + n
    for n, v in M.get('tie', {}).items():
        body.append(f"    assign w_{n} = {v[0]};   // {v[1]}")
    for n, d, w, fs in cp:
        parts = []
        for f in fs:
            pw = P[f['port']][1]
            src = bsl('w_' + f['port'], pw, f.get('plo', 0), f['width'])
            if d == 'in': body.append(f"    assign {src} = {bsl(n, w, f['lsb'], f['width'])};")
            else: parts.append(src)
        if d == 'out':
            cat = '{' + ', '.join(reversed(parts)) + '}' if len(parts) > 1 else parts[0]
            if n == mb:
                body += [f'    wire [{w - 1}:0] m_{n} = {cat};', f'`ifdef {MUT}',
                         f'    assign {n} = {{m_{n}[{w - 1}:2], m_{n}[0], m_{n}[1]}};', '`else', f'    assign {n} = m_{n};', '`endif']
            else:
                body.append(f'    assign {n} = {cat};')
    L += body + [f"    {M['body']} {M.get('inst_params', '')}u_body (".replace('  u_body', ' u_body')]
    L += [',\n'.join(f'        .{p}({conn[p]})' for p in P), '    );', 'endmodule', '']
    open(M['rtl'], 'w').write('\n'.join(L))
    # bench shim: the body's port list around the slot cell (unpacks with the same table)
    S = [f'// GENERATED by physical/qwen_kv_slots/gen_slot.py {name}: body-shaped view of the slot cell for the bench.',
         f"module {name}_bodyview {M.get('shim_params', '')}("]
    S += [',\n'.join(f"    {d} wire {f'[{w - 1}:0] ' if w > 1 else ''}{n}" for n, (d, w) in P.items()), ');']
    seen = set()
    for n, d, w, fs in cp:
        S.append(f"    wire {f'[{w - 1}:0] ' if w > 1 else ''}b_{n};")
        for f in fs:
            pw = P[f['port']][1]
            psl = bsl(f['port'], pw, f.get('plo', 0), f['width']); bs = bsl('b_' + n, w, f['lsb'], f['width'])
            if d == 'in': S.append(f'    assign {bs} = {psl};')
            elif (f['port'], f.get('plo', 0)) not in seen:
                S.append(f'    assign {psl} = {bs};'); seen.add((f['port'], f.get('plo', 0)))
    for n in M.get('open', []):
        S.append(f'    assign {n} = u_slot.w_{n};   // not a pin of the cell: observed through the hierarchy')
    S += [f'    {name} u_slot (.ck({clk}), ' + ', '.join(f'.{n}(b_{n})' for n, _, _, _ in cp) + ');']
    # copies of one body output on several bundles must agree
    cps = {}
    for n, d, w, fs in cp:
        if d != 'out': continue
        for f in fs: cps.setdefault((f['port'], f.get('plo', 0), f['width']), []).append(bsl('b_' + n, w, f['lsb'], f['width']))
    eq = [f'({a} === {v[0]})' for v in cps.values() for a in v[1:]]
    S += ['    wire copies_same = ' + (' && '.join(eq) if eq else "1'b1") + ';', 'endmodule', '']
    open(M['shim'], 'w').write('\n'.join(S))
    print('OK', name, len(rows), 'bundles;', len(cp), 'cell ports;', nbits, 'cell pin bits;', len(unb), 'unbound ranges')
    for r in rows:
        fs = ', '.join((f"UNBOUND {f['width']}" if f['port'] is None else
                        f"{'(credit, against flow) ' if f['against_flow'] else ''}{bsl(f['port'], P[f['port']][1], f['plo'], f['width'])} {f['width']}")
                       for f in r['fields'])
        print(f"  {r['bundle']}[{r['width'] - 1}:0] {r['flow']} {r['peer']} = LSB-first {{ {fs} }}")


main()
