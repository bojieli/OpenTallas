#!/usr/bin/env python3
"""KVJ-A3 (10-17): clock-domain census of the HOST root qkd_host_root_admission on its yosys elaboration (proc only, no
flatten).  For every instance it reports its flip-flop bits per TOP clock port bit (traced through every hierarchy level),
memory bits, macro instances and a generic-cell count, and classifies it as single-clock, single-family (all clocks of
one PLL family, kv_die.HOST_CLK_FAMILY) or mixed (needs splitting or is itself a CDC cell).

usage: clock_tree_census.py elab.json out.json [--top qkd_host_root_admission]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))

FF = re.compile(r'^\$(a?l?dff|adffe|dffe|sdff|sdffe|sdffce|dffsr|dffsre|aldffe|adlatch|dlatch)$')
MEMCLK = ('$memwr', '$memwr_v2', '$memrd', '$memrd_v2', '$mem', '$mem_v2')


def family_map():
    from kv_die import HOST_CLK_FAMILY, HOST_CLK_INFERRED  # noqa: E402
    fam = dict(HOST_CLK_FAMILY, **HOST_CLK_INFERRED)
    out = {}
    for c, f in fam.items():
        m = re.match(r'^(ck_phy|ck_qm_bank)(\d+)$', c)
        out[f'{m.group(1)}[{m.group(2)}]' if m else c] = f
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('elab')
    ap.add_argument('out')
    ap.add_argument('--top', default='qkd_host_root_admission')
    a = ap.parse_args()
    mods = json.loads(Path(a.elab).read_text())['modules']
    fam = family_map()
    top = next(n for n in mods if n == a.top or n.endswith('\\' + a.top) or mods[n].get('attributes', {}).get('top'))
    nodes = []

    def walk(mname, path, bitmap, depth):
        m = mods[mname]
        node = dict(path=path, module=re.sub(r'^\$paramod\$[0-9a-f]+\\|^\$paramod\\', '', mname).split('\\')[0],
                    own_ff=Counter(), ff=Counter(), mem_bits=0, own_cells=0, cells=0, macros=Counter(),
                    children=[], internal_clk=Counter())
        nodes.append(node)
        for mn, mm in m.get('memories', {}).items():
            node['mem_bits'] += int(mm.get('width', 0)) * int(mm.get('size', 0))
        for cn, c in m['cells'].items():
            t = c['type']
            if t in mods and not mods[t].get('attributes', {}).get('blackbox'):
                cb = {}
                cm = mods[t]
                for pn, p in cm['ports'].items():
                    if p['direction'] != 'input':
                        continue
                    conn = c['connections'].get(pn, [])
                    for i, b in enumerate(p['bits']):
                        if i < len(conn) and conn[i] in bitmap:
                            cb[b] = bitmap[conn[i]]
                ch = walk(t, f'{path}/{cn}', cb, depth + 1)
                node['children'].append(ch['path'])
                node['ff'].update(ch['ff'])
                node['mem_bits'] += ch['mem_bits']
                node['cells'] += ch['cells']
                node['macros'].update(ch['macros'])
                node['internal_clk'].update(ch['internal_clk'])
                continue
            if t in mods or not t.startswith('$'):
                node['macros'][t] += 1
                continue
            node['own_cells'] += 1
            if FF.match(t):
                clk = c['connections'].get('CLK') or c['connections'].get('EN')
                w = len(c['connections'].get('Q', []))
                k = bitmap.get(clk[0]) if clk and len(clk) == 1 else None
                if k is None:
                    k = 'internal:' + (str(clk[0]) if clk else '?')
                    node['internal_clk'][f'{path}:{cn}'] += w
                node['own_ff'][k] += w
            elif t in MEMCLK:
                pr = c.get('parameters', {})
                if t.startswith('$mem') and 'SIZE' in pr and 'WIDTH' in pr and t in ('$mem', '$mem_v2'):
                    node['mem_bits'] += int(pr['SIZE'], 2) * int(pr['WIDTH'], 2)
        node['ff'].update(node['own_ff'])
        node['cells'] += node['own_cells']
        return node

    tm = mods[top]
    bm = {}
    for pn, p in tm['ports'].items():
        if p['direction'] == 'input' and pn.startswith('ck'):
            for i, b in enumerate(p['bits']):
                bm[b] = pn if len(p['bits']) == 1 else f'{pn}[{i}]'
    walk(top, 'top', bm, 0)
    for n in nodes:
        fams = sorted({fam.get(k, 'internal' if k.startswith('internal') else 'unknown:' + k) for k in n['ff']})
        n['families'] = fams
        n['klass'] = 'none' if not fams else ('single_clock' if len(n['ff']) == 1 else
                                              ('single_family' if len(fams) == 1 else 'mixed'))
        n['ff_total'] = sum(n['ff'].values())
        for k in ('own_ff', 'ff', 'macros', 'internal_clk'):
            n[k] = dict(n[k])
    Path(a.out).write_text(json.dumps(dict(top=top, nodes=nodes), indent=1))
    tot = nodes[0]
    print(f"top {top}: ff {tot['ff_total']} clocks {len(tot['ff'])} cells {tot['cells']} mem_bits {tot['mem_bits']} "
          f"macros {sum(tot['macros'].values())}")


if __name__ == '__main__':
    main()
