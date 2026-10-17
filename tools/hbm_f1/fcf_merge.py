#!/usr/bin/env python3
"""(fork: every clk_out<k> pin) Replace the clk_out pin's timing() groups of the fc relay ETM (A) by the clk_in -> clk_out combinational arcs of the
all-clocks-deleted export (B), in place.  Refuses if (B) has no combinational clk_in arc."""
import re, sys
A, B = sys.argv[1], sys.argv[2]

def pin_block(t, pin):
    i = t.index(f'pin("{pin}")')
    j = t.index('{', i); d = 0
    for k in range(j, len(t)):
        if t[k] == '{': d += 1
        elif t[k] == '}':
            d -= 1
            if d == 0: return i, k + 1
    raise SystemExit('unbalanced')

def timings(blk):
    out = []; p = 0
    while True:
        i = blk.find('timing()', p)
        if i < 0: return out
        j = blk.index('{', i); d = 0
        for k in range(j, len(blk)):
            if blk[k] == '{': d += 1
            elif blk[k] == '}':
                d -= 1
                if d == 0: out.append(blk[i:k + 1]); p = k + 1; break

ta, tb = open(A).read(), open(B).read()
pins = sorted(set(re.findall(r'pin\("(clk_out\d*)"\)', ta)))
if not pins:
    print('FC_MERGE_FAIL no clk_out pin in', A); sys.exit(2)
for pn in pins:
    a0, a1 = pin_block(ta, pn); b0, b1 = pin_block(tb, pn)
    tb_t = [g for g in timings(tb[b0:b1]) if re.search(r'related_pin\s*:\s*"clk_in"', g)]
    if not tb_t or any('timing_type' in g and 'combinational' not in g for g in tb_t):
        print('FC_MERGE_FAIL no combinational clk_in arc on', pn, 'in', B); sys.exit(2)
    blk = ta[a0:a1]
    for g in timings(blk):
        blk = blk.replace(g, '')
    head = blk[:blk.index('{') + 1]
    rest = blk[blk.index('{') + 1:]
    blk = head + '\n      ' + '\n      '.join(tb_t) + rest
    ta = ta[:a0] + blk + ta[a1:]
    v = re.findall(r'cell_rise.*?values\s*\(\s*"([^"]+)"', tb_t[0], re.S)
    print('FC_MERGE_OK', pn, 'clk_in->', pn, 'cell_rise', v[0].split(',')[:3] if v else None)
open(sys.argv[3], "w").write(ta)
