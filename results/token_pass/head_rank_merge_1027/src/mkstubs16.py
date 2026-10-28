#!/usr/bin/env python3
"""TOK-ALL-16 (from TOK-ALL-15; serdes_link + mesh_ep_core are now REAL): header-only stubs (outputs undriven = 0 in 2-state Verilator) for die partitions OFF the head
spine/chain path (serdes PHY link, mesh/host endpoints, lep0N stage endpoint).  The generated wrappers (boundary
flops, reset/START wavefront) are kept unchanged; only these leaves are emptied."""
import re, sys
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2])
mods = {'ot_s81hd_host_ep_core': 'rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv',
        'ot_s81hd_lep0N_noidx_core': 'rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_core.sv'}
def header(txt, name):
    m = re.search(r'\bmodule\s+' + name + r'\b', txt)
    assert m, name
    i = m.end(); depth = 0
    txt2 = re.sub(r'//[^\n]*', lambda x: ' ' * len(x.group(0)), txt)
    while True:
        c = txt2[i]
        if c == '(': depth += 1
        elif c == ')':
            depth -= 1
        elif c == ';' and depth == 0: break
        i += 1
    return txt2[m.start():i + 1]
s = ['`timescale 1ns/1ps', '// verilator lint_off UNDRIVEN', '// verilator lint_off UNUSED']
for n, f in mods.items():
    s += ['// STUB (TOK-ALL-15, off-path leaf) of ' + f, header((root / f).read_text(), n), 'endmodule', '']
out.write_text('\n'.join(s) + '\n')
print('stubs', list(mods))
