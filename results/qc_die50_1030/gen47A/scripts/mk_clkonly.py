#!/usr/bin/env python3
"""DIE-QC-50/gen47A: gen47 kit ctree.v -> clock-only netlist with the ODB names (ck_ prefix on every clock cell and net,
as native_clock_source grafts them; 'root' and the t_* tap aliases unchanged) for the fixed_tree prebuild adapter.
usage: mk_clkonly.py CTREE_V OUT_V"""
import re, sys
src, out = sys.argv[1:3]
t = open(src).read()
P = lambda n: n if n == 'root' or n.startswith('ck_') else 'ck_' + n
cell = re.compile(r'(?m)^(\s*)(\w+_ASAP7_75t_R)\s+(\w+)\s*\(\s*\.A\((\w+)\)\s*,\s*\.Y\((\w+)\)\s*\);')
n = [0]
def c(m):
    n[0] += 1
    return f'{m[1]}{m[2]} {P(m[3])} (.A({P(m[4])}), .Y({P(m[5])}));'
t = cell.sub(c, t)
a = [0]
def s(m):
    a[0] += 1
    return f'{m[1]}assign {m[2]} = {P(m[3])};'
t = re.sub(r'(?m)^(\s*)assign\s+(\w+)\s*=\s*(\w+)\s*;', s, t)
# wire declarations: prefix every declared clock net
def w(m):
    names = [x.strip() for x in m[2].split(',')]
    return m[1] + ', '.join(P(x) if not x.startswith('t_') else x for x in names) + ';'
t = re.sub(r'(?m)^(\s*wire\s+)([^;]+);', w, t)
open(out, 'w').write(t)
print('CLKONLY cells', n[0], 'assigns', a[0])
