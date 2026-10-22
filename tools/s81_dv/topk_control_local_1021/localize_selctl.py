#!/usr/bin/env python3
"""[ELEM-BKG] Localize the sel_ctl FSM state decode: the combinational next-state block is instantiated once per
register chunk group, each reading its own kept same-edge copy of st (ot_s81pa_rcopy, same D = st_d, same reset leaf
as the consuming group).  Every register keeps its exact next-value expression and edge."""
import re, sys
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text()
assert 'g_nx' not in s
a = s.index('    reg[2:0]st_d;'); b = s.index('    localparam[2:0]N32_INIT_st=C_CLR;')
blk = s[a:b]
decl = re.findall(r'reg\[(\d+):0\](\w+)_d;', blk)
names = [n for _, n in decl]; width = {n: int(w) + 1 for w, n in decl}
uses = re.search(r'    wire          use_c = .*?\n    wire          use_f = .*?\n', s).group(0)
s = s.replace(uses, '')
a = s.index('    reg[2:0]st_d;'); b = s.index('    localparam[2:0]N32_INIT_st=C_CLR;')
# chunk groups (from the registered generate loops)
loops = re.findall(r'generate for\(genvar c=0;c<(\d+);c=c\+1\)begin:g_n32_(\w+)\n', s)
nch = {n: int(k) for k, n in loops}
assert set(nch) == set(names), (set(nch) ^ set(names))
copy = {}; k = 1
for n in names:
    if width[n] == 1 or n == 'st': copy[n] = 0
    else: copy[n] = k; k += nch[n]
NK = k
off = {}; o = 0
for n in names: off[n] = o; o += width[n]
NXW = o
body = blk.replace('reg[', 'reg[', 1)
body = re.sub(r'\bst\b', 'stc', body)
body = body.replace('stc_d', 'st_d')
use_k = re.sub(r'\bst\b', 'stc', uses)
pack = '{' + ','.join(f'{n}_d' for n in reversed(names)) + '}'
gen = (f'    // [ELEM-BKG] {NK} same-edge next-state copies, one per register chunk group; copy0 = original st + 1-bit flags\n'
       f'    localparam integer NXK={NK}, NXW={NXW};\n'
       f'    wire[NXK*NXW-1:0]nx_bus;\n    wire[3*NXK-1:0]st_k;\n'
       f'    assign st_k[2:0]=st;\n'
       f'    generate for(genvar k=0;k<NXK;k=k+1)begin:g_nx\n'
       f'    wire[2:0]stc=st_k[3*k+:3];\n' + use_k + body +
       f'    assign nx_bus[NXW*k+:NXW]={pack};\n'
       f'    end endgenerate\n')
s = s[:a] + gen + s[b:]
# registered groups read their own copy; st copies reset with the consuming group's leaf
for n in names:
    m = re.search(r'(generate for\(genvar c=0;c<\d+;c=c\+1\)begin:g_n32_%s\n.*?end endgenerate\n)' % n, s, re.S)
    assert m, n; g = m.group(1)
    src = f'nx_bus[NXW*({copy[n]}+c*{1 if copy[n] else 0})+{off[n]}'
    if width[n] == 1:
        g2 = g.replace(f'else {n}<={n}_d;', f'else {n}<={src}];')
    else:
        g2 = g.replace(f'else {n}[LO+:SW]<={n}_d[LO+:SW];', f'else {n}[LO+:SW]<={src}+LO+:SW];')
    assert g2 != g, n
    if copy[n]:
        rst = re.search(r'negedge rst_n_profile\[(\d+)\+c\]', g).group(1)
        g2 = g2.replace('    end endgenerate\n',
            f'      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID({copy[n]}+c))u_stk(.clk(clk),.rst_n(rst_n_profile[{rst}+c]),.d(nx_bus[{off["st"]}+:3]),.q(st_k[3*({copy[n]}+c)+:3]));\n    end endgenerate\n')
    s = s.replace(g, g2)
p.write_text(s)
print('NXK', NK, 'NXW', NXW, {n: copy[n] for n in names})
