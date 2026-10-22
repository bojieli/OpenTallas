#!/usr/bin/env python3
"""KV-MU7 10-20: exhaustive check of the bench's functional ASAP7 combinational cell models against the official
asap7sc7p5t_*_RVT models (their gate-primitive Function sections; specify/timing dropped).
usage: gen_cell_check.py asap7_func_cells.v OFFICIAL_DIR out.sv"""
import re
import sys
from pathlib import Path

mine, off_dir, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
ms = Path(mine).read_text()
cells = {}
for m in re.finditer(r'module\s+(\w+_ASAP7_75t_R)\((.*?)\);', ms):
    name, ports = m.group(1), m.group(2)
    if name.startswith(('DFF', 'TIE')):
        continue
    ins = re.match(r'input\s+([\w,]+),\s*output\s+(\w+)', ports)
    cells[name] = (ins.group(1).split(','), ins.group(2))
off = {}
for f in sorted(off_dir.glob('asap7sc7p5t_*RVT*.v')):
    s = f.read_text()
    for m in re.finditer(r'module\s+(\w+_ASAP7_75t_R)\s*\((.*?)\);(.*?)endmodule', s, re.S):
        if m.group(1) in cells:
            body = re.sub(r'specify.*?endspecify', '', m.group(3), flags=re.S)
            off[m.group(1)] = 'module OFF_%s (%s);%s\nendmodule\n' % (m.group(1), m.group(2), body)
missing = sorted(set(cells) - set(off))
L = ['`timescale 1ns/1ps', ms, *off.values(), 'module tb_cell_check;', ' integer errors=0,checked=0,v;']
for n, (ins, o) in sorted(cells.items()):
    if n not in off:
        continue
    k = len(ins)
    L.append(' reg [%d:0] i_%s; wire a_%s, b_%s;' % (k - 1, n, n, n))
    conn = ','.join('.%s(i_%s[%d])' % (p, n, j) for j, p in enumerate(ins))
    L.append(' %s u_m_%s(%s,.%s(a_%s));' % (n, n, conn, o, n))
    L.append(' OFF_%s u_o_%s(%s,.%s(b_%s));' % (n, n, conn, o, n))
L.append(' initial begin')
for n, (ins, o) in sorted(cells.items()):
    if n not in off:
        continue
    L.append('  for(v=0;v<%d;v=v+1)begin i_%s=v;#1;checked=checked+1;if(a_%s!==b_%s)begin errors=errors+1;'
             '$display("ERR %s in=%%b mine %%b official %%b",i_%s,a_%s,b_%s);end end' % (2 ** len(ins), n, n, n, n, n, n, n))
L.append('  if(errors==0&&%d==0)$display("PASS CELL_CHECK %d combinational cells, %%0d input vectors, all equal to the official models",checked);' % (len(missing), len(off)))
L.append('  else $display("FAIL CELL_CHECK errors=%%0d missing_official=%s",errors);' % (' '.join(missing) or 'none'))
L.append('  $finish;\n end\nendmodule')
Path(out).write_text('\n'.join(L) + '\n')
print('cells', len(cells), 'official', len(off), 'missing', missing)
