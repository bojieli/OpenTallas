#!/usr/bin/env python3
"""HBM-ELEM13/HC-TAIL 10-21: fold constant inputs of mapped Liberty cells in a yosys JSON netlist (before
bound_fanout_clone.py).

Why: the per-module ABC map (tail_child_hc9/nl.sh) maps every module separately and flattens afterwards, so constant
module ports survive as 1'b0/1'b1 pins on mapped cells (k3/k4: ~128k constant pin bits).  Since main 45386657d the
native census (tools/ref_tile/native_census.py, rule native-liberty-constant-identities) counts a cell whose proven
constant inputs reduce it to an identity / inverse of ONE dynamic input as transparent, so a driver feeding many such
cells carries their loads (k4 gate: 290 drivers, max 181).  The cloner bounds loads per net and cannot see that.

What: per combinational single-output cell with >= 1 constant input, the Liberty function is reduced over the
remaining inputs (truth table):
  constant      -> the output bits become that constant at every load, the cell is removed;
  identity of X -> loads of the output move to X, the cell is removed (a top-port output keeps a BUFx2 instead);
  inverse of X  -> the cell is replaced by INVx1 (A = X), so the census / cloner see an ordinary inverter;
  otherwise     -> kept (a real multi-input function).
Iterated to a fixed point (folding creates new constants).  Sequential cells are untouched.  Function is unchanged by
construction; the native lockstep bench of the final netlist is the witness.
usage: const_identity_fold.py IN.json OUT.json --top TOP --liberty L.lib [--liberty ...]
"""
import argparse, itertools, json, re, sys, collections


def parse_liberty(paths):
    funcs = {}
    for p in paths:
        txt = open(p).read()
        for m in re.finditer(r'\bcell\s*\(\s*"?([\w]+)"?\s*\)\s*\{', txt):
            name = m.group(1)
            # cell body: brace matching
            i, depth = m.end(), 1
            while depth and i < len(txt):
                c = txt[i]
                depth += (c == '{') - (c == '}')
                i += 1
            body = txt[m.end():i]
            seq = bool(re.search(r'\b(ff|latch|statetable)\s*\(', body))
            pins = {}
            for pm in re.finditer(r'\bpin\s*\(\s*"?(\w+)"?\s*\)\s*\{', body):
                j, d = pm.end(), 1
                while d and j < len(body):
                    d += (body[j] == '{') - (body[j] == '}')
                    j += 1
                pb = body[pm.end():j]
                dm = re.search(r'direction\s*:\s*"?(\w+)"?', pb)
                fm = re.search(r'\bfunction\s*:\s*"([^"]*)"', pb)
                pins[pm.group(1)] = (dm.group(1) if dm else None, fm.group(1) if fm else None)
            funcs[name] = (seq, pins)
    return funcs


def to_py(f):
    f = f.replace('!', ' not ').replace('*', ' and ').replace('+', ' or ').replace('^', ' != ')
    f = re.sub(r'\b1\b', ' True ', re.sub(r'\b0\b', ' False ', f))
    return f.strip()


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('inp'); a.add_argument('out'); a.add_argument('--top', required=True)
    a.add_argument('--liberty', action='append', required=True)
    a.add_argument('--inv', default='INVx1_ASAP7_75t_R'); a.add_argument('--buf', default='BUFx2_ASAP7_75t_R')
    args = a.parse_args()
    lib = parse_liberty(args.liberty)
    d = json.load(open(args.inp))
    top = d['modules'][args.top]
    cells = top['cells']
    port_bits = set()
    for p in top['ports'].values():
        if p['direction'] == 'output':
            port_bits.update(b for b in p['bits'] if isinstance(b, int))
    # loads index: net bit -> list of (cell, pin, idx)
    loads = collections.defaultdict(list)
    for cn, c in cells.items():
        for pn, bits in c['connections'].items():
            if c['port_directions'].get(pn) == 'input':
                for k, b in enumerate(bits):
                    if isinstance(b, int):
                        loads[b].append((cn, pn, k))
    code_cache = {}
    stats = collections.Counter()
    work = [cn for cn, c in cells.items()
            if any(isinstance(b, str) for pn, bs in c['connections'].items() if c['port_directions'].get(pn) == 'input' for b in bs)]
    seen_round = 0
    while work:
        seen_round += 1
        nxt = set()
        for cn in work:
            c = cells.get(cn)
            if c is None:
                continue
            info = lib.get(c['type'])
            if info is None or info[0]:
                continue
            outs = [pn for pn, dr in c['port_directions'].items() if dr == 'output']
            if len(outs) != 1:
                continue
            fn = info[1].get(outs[0], (None, None))[1]
            if not fn:
                continue
            ins = [pn for pn, dr in c['port_directions'].items() if dr == 'input']
            if any(len(c['connections'][pn]) != 1 for pn in ins + outs):
                continue
            cval = {pn: c['connections'][pn][0] for pn in ins}
            const = {pn: v == '1' for pn, v in cval.items() if isinstance(v, str) and v in ('0', '1')}
            if not const:
                continue
            dyn = [pn for pn in ins if pn not in const]
            key = (c['type'], tuple(sorted(const.items())))
            if key not in code_cache:
                expr = compile(to_py(fn), c['type'], 'eval')
                tt = []
                for vals in itertools.product((False, True), repeat=len(dyn)):
                    env = dict(const); env.update(zip(dyn, vals))
                    tt.append(bool(eval(expr, {}, env)))
                kind = None
                if all(t == tt[0] for t in tt):
                    kind = ('const', tt[0])
                else:
                    for i, pn in enumerate(dyn):
                        col = [vals[i] for vals in itertools.product((False, True), repeat=len(dyn))]
                        if tt == col:
                            kind = ('id', pn); break
                        if tt == [not v for v in col]:
                            kind = ('inv', pn); break
                code_cache[key] = kind
            kind = code_cache[key]
            if kind is None:
                stats['kept_multi'] += 1
                continue
            ob = c['connections'][outs[0]][0]
            if not isinstance(ob, int):
                continue
            if kind[0] == 'inv':
                x = cval[kind[1]]
                del cells[cn]
                for pn, bits in c['connections'].items():
                    if c['port_directions'][pn] == 'input':
                        for b in bits:
                            if isinstance(b, int):
                                loads[b] = [l for l in loads[b] if l[0] != cn]
                cells[cn] = {'hide_name': c.get('hide_name', 1), 'type': args.inv, 'parameters': {}, 'attributes': {},
                             'port_directions': {'A': 'input', 'Y': 'output'}, 'connections': {'A': [x], 'Y': [ob]}}
                loads[x].append((cn, 'A', 0))
                stats['to_inv'] += 1
                continue
            if ob in port_bits:
                if kind[0] == 'id':
                    x = cval[kind[1]]
                    for pn, bits in c['connections'].items():
                        if c['port_directions'][pn] == 'input':
                            for b in bits:
                                if isinstance(b, int):
                                    loads[b] = [l for l in loads[b] if l[0] != cn]
                    cells[cn] = {'hide_name': c.get('hide_name', 1), 'type': args.buf, 'parameters': {}, 'attributes': {},
                                 'port_directions': {'A': 'input', 'Y': 'output'}, 'connections': {'A': [x], 'Y': [ob]}}
                    loads[x].append((cn, 'A', 0))
                    stats['to_buf_port'] += 1
                else:
                    stats['const_port_kept'] += 1
                continue
            # remove the cell and move its loads
            for pn, bits in c['connections'].items():
                if c['port_directions'][pn] == 'input':
                    for b in bits:
                        if isinstance(b, int):
                            loads[b] = [l for l in loads[b] if l[0] != cn]
            del cells[cn]
            new = ('1' if kind[1] else '0') if kind[0] == 'const' else cval[kind[1]]
            for (ln, lp, k) in loads.pop(ob, []):
                lc = cells.get(ln)
                if lc is None:
                    continue
                lc['connections'][lp][k] = new
                if isinstance(new, int):
                    loads[new].append((ln, lp, k))
                else:
                    nxt.add(ln)
            stats['removed_' + kind[0]] += 1
        work = list(nxt)
    json.dump(d, open(args.out, 'w'))
    remaining = sum(1 for c in cells.values() if not lib.get(c['type'], (True,))[0]
                    and any(isinstance(b, str) for pn, bs in c['connections'].items()
                            if c['port_directions'].get(pn) == 'input' for b in bs))
    print('FOLD rounds=%d %s comb_cells_with_const_inputs_left=%d' % (seen_round, dict(stats), remaining))


if __name__ == '__main__':
    main()
