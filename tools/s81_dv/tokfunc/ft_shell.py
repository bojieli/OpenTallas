#!/usr/bin/env python3
"""ft_shell.py -- generate a pass-through shell of a bound partition type (TOK-VERIFY-1 S2, COORD 11-10).

A cut that carries a lane through a compute partition (an ft port pair of a slice / leaf / svc partition) does not
need that partition's compute.  The shell keeps, VERBATIM from the bind-emitted type (comments stripped), exactly the
fan-in cone of the kept output ports, through infrastructure cells only:
    ot_dp_* (st, dly, clk_landing, landing_collect / face, rrelay, rsync, or / and, ...), ot_meso_*, assigns.
The cone stops at module input ports.  If the cone needs a net driven by anything else (a leaf / compute instance, an
always block), the shell is REFUSED for that partition (the cut then keeps the whole partition) -- a feed-through that
depends on compute is not a pass-through.  Every declaration is kept (unused wires are harmless).  The shell module is
named <type>__ftshell and has only the kept ports.

--mutant PORT:+1 (generator option, negative control): adds one ot_dp_st stage, verbatim cell form, in front of
the kept output port PORT; the cut's lane through that shell must then FAIL (lane_arrival on the cut).
"""
import re
from collections import defaultdict

ID = r'[A-Za-z_][A-Za-z0-9_$]*'
INFRA = re.compile(r'^(ot_dp_|ot_meso_)')
# output pins of the infrastructure cells (everything else on them is an input)
OUTPINS = {'q', 'eq', 'o', 'y', 'ready', 'fault', 'ready_o', 'fault_o', 'sync_rst_n', 'r_d', 'r_v', 'r_lap_ok',
           'r_glo_ok', 'r_ghi_ok', 'p_v', 'p_d', 'rst_o', 'fclk_o'}
DECL = re.compile(r'^\s*(wire|reg|logic|localparam|parameter|genvar|integer)\b')


def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', '', t)


def split_conns(body):
    out, i, n = {}, 0, len(body)
    while True:
        j = body.find('.', i)
        if j < 0:
            break
        m = re.match(r'\.\s*(' + ID + r')\s*\(', body[j:])
        if not m:
            i = j + 1
            continue
        k = j + m.end()
        depth, s = 1, k
        while k < n and depth:
            depth += {'(': 1, ')': -1}.get(body[k], 0)
            k += 1
        out[m.group(1)] = body[s:k - 1].strip()
        i = k
    return out


def ids(expr):
    return [x for x in re.findall(ID, expr or '') if not re.match(r"^\d", x)]


def statements(body):
    """split a module body into top-level statements; always/initial/generate blocks stay whole (begin/end depth)"""
    out, cur, depth, i = [], [], 0, 0
    toks = re.split(r'(;|\bbegin\b|\bend\b|\bendgenerate\b|\bgenerate\b)', body)
    for t in toks:
        cur.append(t)
        if t in ('begin', 'generate'):
            depth += 1
        elif t in ('end', 'endgenerate'):
            depth -= 1
            if depth == 0:
                s = ''.join(cur).strip()
                # an `always ... begin ... end` closes here; the trailing statement keeps its text
                out.append(s)
                cur = []
        elif t == ';' and depth == 0:
            out.append(''.join(cur).strip()[:-1].strip())
            cur = []
    if ''.join(cur).strip():
        out.append(''.join(cur).strip())
    return [s for s in out if s and s != ';']


def parse_type(text, mod):
    t = strip_comments(text)
    m = re.search(r'\bmodule\s+' + mod + r'\b', t)
    e = t.index('endmodule', m.start())
    src = t[m.start():e]
    # header: module NAME [#( params )] ( ports );
    hm = re.match(r'module\s+' + mod + r'\s*(#\s*\((.*?)\))?\s*\((.*?)\)\s*;', src, flags=re.S)
    params, ports_txt = hm.group(2), hm.group(3)
    ports = {}
    for d in re.split(r',(?![^\[]*\])', ports_txt):
        pm = re.match(r'\s*(input|output|inout)\s+(.*?)(' + ID + r')\s*$', d.strip(), flags=re.S)
        if pm:
            ports[pm.group(3)] = dict(dir=pm.group(1), decl=d.strip())
    body = src[hm.end():]
    return dict(params=params, ports=ports, stmts=statements(body))


def build(text, mod, keep_out, mutant=None):
    """returns (shell verilog text, kept port names, report) or raises ValueError (refused)"""
    T = parse_type(text, mod)
    drv = defaultdict(list)       # net -> [(stmt index, kind)]
    info = {}
    for k, s in enumerate(T['stmts']):
        if DECL.match(s):
            # `wire X = expr` is a declaration AND a driver of X (the bind writes `wire rst_n = rst_n_t18;`)
            dm = re.match(r'\s*wire\b\s*(?:signed\s*)?(?:\[[^\]]*\])?\s*(' + ID + r')\s*=\s*(.+)$', s, flags=re.S)
            info[k] = ('decl', [dm.group(1)], ids(dm.group(2))) if dm else ('decl', [], [])
            for n in info[k][1]:
                drv[n].append(k)
            continue
        a = re.match(r'assign\s+(.+?)\s*=\s*(.+)$', s, flags=re.S)
        if a:
            outs, ins = ids(a.group(1))[:1], ids(a.group(2))
            info[k] = ('assign', outs, ins)
        elif re.match(r'(always|initial)\b', s):
            outs = list(set(re.findall(r'(' + ID + r')\s*(?:\[[^\]]*\])?\s*<?=(?!=)', s)))
            info[k] = ('proc', outs, ids(s))
        else:
            im = re.match(r'(' + ID + r')\s*(#\s*\((.*)\))?\s*(' + ID + r')\s*\((.*)\)\s*$', s, flags=re.S)
            if not im:
                info[k] = ('other', [], ids(s))
                continue
            cm, conns = im.group(1), split_conns(im.group(5))
            if INFRA.match(cm):
                outs = [n for p, e in conns.items() if p in OUTPINS for n in ids(e)]
                ins = [n for p, e in conns.items() if p not in OUTPINS for n in ids(e)]
                info[k] = ('infra', outs, ins)
            else:
                allnets = [n for e in conns.values() for n in ids(e)]
                info[k] = ('leaf:' + cm, allnets, allnets)
        for n in info[k][1]:
            drv[n].append(k)
    keep, inports, todo, seen, bad = set(), set(), [p for p in keep_out], set(), []
    params = set(ids(T['params'] or ''))
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in T['ports'] and T['ports'][n]['dir'] == 'input':
            inports.add(n)
            continue
        if n in params:
            continue
        ds = drv.get(n, [])
        if not ds:
            if n not in T['ports']:
                continue            # parameter / localparam / genvar / constant name
        # leaf pins have no known direction here: a leaf counts as a driver only when no infrastructure cell, assign
        # or always block drives the net (a leaf merely READING rst_n must not refuse the shell)
        known = [k for k in ds if not info[k][0].startswith('leaf:')]
        for k in (known or ds):
            kind, outs, ins = info[k]
            if kind == 'decl':          # kept anyway with every declaration; follow its initializer
                todo.extend(ins)
            elif kind in ('infra', 'assign'):
                if k not in keep:
                    keep.add(k)
                    todo.extend(ins)
            else:
                bad.append((n, kind))
    if bad:
        raise ValueError(f'{mod}: pass-through cone reaches non-infrastructure drivers {sorted(set(bad))[:6]}')
    kept_ports = [p for p in T['ports'] if p in inports or p in keep_out]
    hdr = f'module {mod}__ftshell' + (f' #({T["params"]})' if T['params'] else '') + ' (\n    ' + \
          ',\n    '.join(re.sub(r'\s+', ' ', T['ports'][p]['decl']) for p in kept_ports) + '\n);'
    body = [s + ';' for k, s in enumerate(T['stmts']) if info[k][0] == 'decl']
    stmts = [T['stmts'][k] for k in sorted(keep)]
    mut = None
    if mutant:
        port, d = mutant.rsplit(':', 1)
        if int(d) != 1 or port not in keep_out:
            raise ValueError(f'mutant {mutant}: only PORT:+1 on a kept output port')
        # retarget the driver of PORT to an internal net and add one ot_dp_st (data + epoch) in front of PORT
        k = [k for k in keep if port in info[k][1]]
        if len(k) != 1:
            raise ValueError(f'mutant {mutant}: port has {len(k)} drivers')
        i = sorted(keep).index(k[0])
        w = re.search(r'\[(\d+):0\]', T['ports'][port]['decl'])
        hi = int(w.group(1)) if w else 0
        stmts[i] = re.sub(r'\b' + port + r'\b', f'{port}__mut', stmts[i])
        body.append(f'wire [{hi}:0] {port}__mut;')
        ck = re.search(r'\.clk\s*\(([^()]*)\)', T['stmts'][k[0]])
        rs = re.search(r'\.rst_n\s*\(([^()]*)\)', T['stmts'][k[0]])
        ck, rs = (ck.group(1).strip() if ck else 'clk'), (rs.group(1).strip() if rs else "1'b1")
        stmts.append(f'ot_dp_st #(.W({hi})) u_mut_{port} (.clk({ck}), .rst_n({rs}), .d({port}__mut[{hi - 1}:0]), '
                     f'.ea({port}__mut[{hi}]), .q({port}[{hi - 1}:0]), .eq({port}[{hi}]))')
        mut = dict(port=port, stage='ot_dp_st', note='MUTANT: +1 stage in front of the port (must FAIL)')
    txt = '\n'.join(['`timescale 1ns/1ps', '`default_nettype none',
                     f'// GENERATED by ft_shell.py from bound type {mod}: pass-through cone of {sorted(keep_out)}, '
                     f'{len(keep)} cells/assigns verbatim.  Do not edit.', hdr] +
                    ['    ' + s for s in body] + ['    ' + (s if s.endswith(';') or s.endswith('end') else s + ';')
                                                   for s in stmts] + ['endmodule', '`default_nettype wire', ''])
    return txt, kept_ports, dict(type=mod, kept_cells=len(keep), statements=len(T['stmts']), ports=len(kept_ports),
                                 of_ports=len(T['ports']), mutant=mut)
