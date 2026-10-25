#!/usr/bin/env python3
"""Composition top for the split-exactness check: the remainder core (plan pins) + the two CORE-HBM lanes3 pieces
(ot_hbm_hc_bankq_lanes3_core; lanes0_2 = member groups 0..2, lanes3_5 = 3..5, lgk <-> group G0+k as in
canonical_ports_split.json) wired from the member-pin sources of the master (map.json), with the master's port list.
  comp.py MAP.json CORE LANES3_PORTS.json OUT.sv  [--mutant BUS:BIT]  (mutant: invert one remainder->piece net)"""
import json, sys, re, argparse
ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('core'); ap.add_argument('lports'); ap.add_argument('out')
ap.add_argument('--mutant', default='')
a = ap.parse_args()
M = json.load(open(a.map)); src = M['member_src']; buses = M['buses']; tbb = M['top_bus_bits']
LP = json.load(open(a.lports))          # [[name, dir, width, lsb]]
tp = M['top_ports']
L = ['`default_nettype none', 'module cmp_top (' + ', '.join(tp) + ');']
for pn, (d, w) in tp.items():
    L.append(f"    {d} wire {'' if w == 1 else f'[{w-1}:0] '}{pn};")
for b, (w, d) in buses.items():
    L.append(f'    wire [{w-1}:0] w_{b};')
driven = {}
for b, (w, d) in buses.items():
    if b in tbb:
        for k, mi in enumerate(tbb[b]):
            ref = f'{b}[{mi}]' if tp[b][1] > 1 else b
            if d == 'input':
                L.append(f'    assign w_{b}[{k}] = {ref};')
            else:
                L.append(f'    assign {ref} = w_{b}[{k}];'); driven[(b, mi)] = 1
mb, mi_ = (a.mutant.split(':') + [''])[:2] if a.mutant else ('', '')
def expr(s):
    if s[0] == 'const':
        return "1'b" + s[1]
    if s[0] == 'pin':
        e = f'w_{s[1]}[{s[2]}]'
        if s[1] == mb and str(s[2]) == mi_:
            e = '~' + e                   # MUTANT
        return e
    if s[0] == 'top':
        return f'{s[1]}[{s[2]}]' if tp[s[1]][1] > 1 else s[1]
    raise SystemExit(f'bad source {s}')
shared = {'clk': 'clk', 'rst_n': 'rst_n', 'gov_i': 'gov_i', 'ss_i': 'ss_i'}
bad = []
for inst, g0 in (('u_l02', 0), ('u_l35', 3)):
    conns = []
    for nm, d, w, _ in LP:
        k, p = int(nm[2]), nm[4:]
        g = g0 + k
        if d == 'input':
            bits = []
            for i in range(w):
                s = src[f'{g}.{p}.{i}']
                if p in shared:          # one pin feeds the 3 groups x 8 bits: every member bit must be the same net
                    for gg in range(g0, g0 + 3):
                        for ii in range(8 if p == 'ss_i' else 1):
                            if src[f'{gg}.{p}.{ii}'] != s:
                                bad.append((inst, p, gg, ii, src[f'{gg}.{p}.{ii}'], s))
                bits.append(expr(s))
            conns.append(f'.{nm}({{' + ', '.join(reversed(bits)) + '})')
        else:
            wn = f'{inst}_{nm}'
            L.append(f'    wire [{w-1}:0] {wn};')
            for i in range(w):
                s = src[f'{g}.{p}.{i}']
                if s[0] == 'pin':
                    L.append(f'    assign w_{s[1]}[{s[2]}] = {wn}[{i}];')
                elif s[0] == 'top':
                    ref = f'{s[1]}[{s[2]}]' if tp[s[1]][1] > 1 else s[1]
                    L.append(f'    assign {ref} = {wn}[{i}];'); driven[(s[1], s[2])] = 1
                else:
                    bad.append(('output to', s))
            conns.append(f'.{nm}({wn})')
    L.append(f'    ot_hbm_hc_bankq_lanes3_core {inst} (' + ', '.join(conns) + ');')
for pn, cb in M.get('top_const_out', {}).items():
    for i, v in cb:
        L.append(f"    assign {pn}[{i}] = 1'b{v};" if tp[pn][1] > 1 else f"    assign {pn} = 1'b{v};"); driven[(pn, i)] = 1
for pn, fl in M.get('top_feedthrough', {}).items():      # partition-level wire of the master (not in any piece)
    for i, src_p, j in fl:
        lhs = f'{pn}[{i}]' if tp[pn][1] > 1 else pn
        rhs = f'{src_p}[{j}]' if tp[src_p][1] > 1 else src_p
        L.append(f'    assign {lhs} = {rhs};')
L.append(f'    {a.core} u_core (' + ', '.join(f'.{b}(w_{b})' for b in buses) + ');')
L.append('endmodule')
if bad:
    raise SystemExit(f'COMPOSE FAIL {bad[:5]}')
open(a.out, 'w').write('\n'.join(L) + '\n')
print('wrote', a.out)
