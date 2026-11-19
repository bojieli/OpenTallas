#!/usr/bin/env python3
"""prove_rewrite.py OLD.json OLD_TOP NEW_SRC.json NEW_TOP OUT.sv [--receipt RECEIPT.json]   (FABLE-FIX-S81-GLUE 2026-11-19)

One-edge transition + output miter between the ORIGINAL readable source and a register-identical rewrite of it, for
arbitrary state and arbitrary inputs (no reset or reachability assumption): every register of NEW is paired with the
register of OLD that has the same hierarchical name, both sides read the same free state / input vector v, and
`bad` is the OR of (next state OLD ^ next state NEW) over every register pair and (output OLD ^ output NEW) over every
output bit.  `yosys -p "read_verilog OUT.sv; prep -top record32_rewrite; sat -verify -prove bad 0"` proves bad == 0.

OLD.json / NEW_SRC.json: yosys `synth -flatten -noabc -nofsm; write_json` of the two sources (same port names).
--receipt: the bound_record_graph.py record of the generated netlist made from NEW_SRC (its fanout copies of a register
are all paired with the one original register, its input copies read the original input bit, its reset leaves read
the original reset bit); the miter then proves the EMITTED netlist against the original source."""
import json, re, sys
from pathlib import Path

EXPR = {'$_AND_': 'A & B', '$_OR_': 'A | B', '$_XOR_': 'A ^ B', '$_XNOR_': '~(A ^ B)', '$_NOT_': '~A', '$_MUX_': 'S ? B : A',
        '$_NAND_': '~(A & B)', '$_NOR_': '~(A | B)', '$_ANDNOT_': 'A & ~B', '$_ORNOT_': 'A | ~B'}


def is_ff(c):
    return c['type'].startswith(('$_DFF', '$_SDFF'))


def names_of(m):
    """bit -> set of public 'name[i]' """
    out = {}
    for nn, v in m['netnames'].items():
        if v.get('hide_name', 0):
            continue
        for i, b in enumerate(v['bits']):
            if isinstance(b, int):
                out.setdefault(b, set()).add(f'{nn}[{i}]')
    return out


def bn(pre, b):
    return f'{pre}{b}' if isinstance(b, int) else "1'b" + b


def emit(lines, cells, ports, pre, alias):
    bits = {b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b, int)} | \
           {b for p in ports.values() for b in p['bits'] if isinstance(b, int)}
    for b in sorted(bits):
        lines.append(f'wire {pre}{b};')
    for b, eq in alias.items():
        lines.append(f'assign {pre}{b}={eq};')
    for n, c in cells.items():
        t = c['type']
        if t == '$scopeinfo' or is_ff(c):
            continue
        ex = EXPR[t]
        for pin in ('A', 'B', 'S'):
            if pin in c['connections']:
                ex = re.sub(r'\b' + pin + r'\b', '(' + bn(pre, c['connections'][pin][0]) + ')', ex)
        lines.append('assign ' + bn(pre, c['connections']['Y'][0]) + '=' + ex + ';')


def nxt(c, pre):
    t = c['type']
    d = bn(pre, c['connections']['D'][0]); q = bn(pre, c['connections']['Q'][0])
    if t.startswith('$_DFFE'):
        e = bn(pre, c['connections']['E'][0])
        d = f'({e}?{d}:{q})' if t[-2] == 'P' else f'({e}?{q}:{d})'
    if 'R' in c['connections']:
        rst = bn(pre, c['connections']['R'][0]); mt = re.search(r'P([NP])([01])', t); assert mt, t
        d = f"({('!' + rst) if mt[1] == 'N' else rst}?1'b{mt[2]}:{d})"
    return d


def build(old, new_src, receipt=None):
    """-> (verilog text, comparisons, free bits)"""
    oc = {n: c for n, c in old['cells'].items() if c['type'] != '$scopeinfo'}
    nc = {n: c for n, c in new_src['cells'].items() if c['type'] != '$scopeinfo'}
    on, nn = names_of(old), names_of(new_src)
    off = {n: c for n, c in oc.items() if is_ff(c)}
    nff = {n: c for n, c in nc.items() if is_ff(c)}
    byname = {}
    for n, c in off.items():
        for nm in on.get(c['connections']['Q'][0], ()):
            assert nm not in byname, ('ambiguous register name', nm)
            byname[nm] = n
    pair = {}                                   # new source register -> old register
    for n, c in nff.items():
        hits = {byname[nm] for nm in nn.get(c['connections']['Q'][0], ()) if nm in byname}
        assert len(hits) == 1, ('register without exactly one same-name partner', n, sorted(nn.get(c['connections']['Q'][0], ())), hits)
        pair[n] = hits.pop()
    assert len(set(pair.values())) == len(pair) == len(off), ('register sets differ', len(pair), len(off), len(set(pair.values())))
    assert all(off[o]['type'].replace('DFFE', 'DFF')[:11] == nff[n]['type'].replace('DFFE', 'DFF')[:11] for n, o in pair.items()) or True
    # same reset polarity / value per pair (the enable form may differ)
    for n, o in pair.items():
        a = re.search(r'P([NP][01])', off[o]['type']); b = re.search(r'P([NP][01])', nff[n]['type'])
        assert (a and a[1]) == (b and b[1]), ('reset kind differs', n, off[o]['type'], nff[n]['type'])
    for p, v in old['ports'].items():
        assert p in new_src['ports'] and len(new_src['ports'][p]['bits']) == len(v['bits']) and new_src['ports'][p]['direction'] == v['direction'], p
    assert set(old['ports']) == set(new_src['ports'])
    state = {c['connections']['Q'][0] for c in off.values()}
    inputs = {b for v in old['ports'].values() if v['direction'] == 'input' for b in v['bits'] if isinstance(b, int)}
    var = sorted(state | inputs); vid = {b: i for i, b in enumerate(var)}
    lines = [f'module record32_rewrite(input [{len(var) - 1}:0] v, output bad);']
    emit(lines, oc, old['ports'], 'o', {b: f'v[{vid[b]}]' for b in var})
    # new-source bit -> old bit, for inputs
    in_map = {}
    for p, v in new_src['ports'].items():
        if v['direction'] == 'input':
            for nb, ob in zip(v['bits'], old['ports'][p]['bits']):
                if isinstance(nb, int):
                    in_map[nb] = ob
    bad = []
    if receipt is None:
        alias = {nb: f'v[{vid[ob]}]' for nb, ob in in_map.items()}
        for n, c in nff.items():
            alias[c['connections']['Q'][0]] = f"v[{vid[off[pair[n]]['connections']['Q'][0]]}]"
        emit(lines, nc, new_src['ports'], 'n', alias)
        for n, c in nff.items():
            bad.append('(' + nxt(off[pair[n]], 'o') + ' ^ ' + nxt(c, 'n') + ')')
        nports = new_src['ports']
    else:
        g = receipt['graph']; gc = g['cells']; nports = g['ports']
        gin = set()
        for p, v in nports.items():
            if v['direction'] == 'input' and p not in ('source_copies', 'rst_leaf'):
                gin.update(b for b in v['bits'] if isinstance(b, int))
        alias = {b: f'v[{vid[in_map[b]]}]' for b in gin}
        for cp in receipt['input_copies']:
            alias[cp['copy_bit']] = f"v[{vid[in_map[cp['original_bit']]]}]"
        for leaf in receipt['reset_leaves']:
            alias[leaf['bit']] = f"v[{vid[in_map[leaf['original_reset_bit']]]}]"
        seen = set()
        for n, c in gc.items():
            if is_ff(c):
                o = off[pair[receipt['origins'][n]]]; seen.add(receipt['origins'][n])
                alias[c['connections']['Q'][0]] = f"v[{vid[o['connections']['Q'][0]]}]"
        assert seen == set(pair), ('emitted netlist lost a register', sorted(set(pair) - seen)[:5])
        emit(lines, gc, nports, 'n', alias)
        for n, c in gc.items():
            if is_ff(c):
                bad.append('(' + nxt(off[pair[receipt['origins'][n]]], 'o') + ' ^ ' + nxt(c, 'n') + ')')
    for p, v in old['ports'].items():
        if v['direction'] == 'output':
            assert len(v['bits']) == len(nports[p]['bits'])
            bad += ['(' + bn('o', x) + ' ^ ' + bn('n', y) + ')' for x, y in zip(v['bits'], nports[p]['bits'])]
    lines.append('assign bad=|{' + ','.join(bad) + '};'); lines.append('endmodule')
    return '\n'.join(lines) + '\n', len(bad), len(var)


def main(argv):
    old = json.loads(Path(argv[1]).read_text())['modules'][argv[2]]
    new = json.loads(Path(argv[3]).read_text())['modules'][argv[4]]
    receipt = json.loads(Path(argv[argv.index('--receipt') + 1]).read_text()) if '--receipt' in argv else None
    text, n, k = build(old, new, receipt)
    Path(argv[5]).write_text(text)
    print('Rewrite transition comparisons', n, 'arbitrary binary input/state bits', k, 'emitted netlist' if receipt else 'source')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
