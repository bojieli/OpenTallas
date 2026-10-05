#!/usr/bin/env python3
"""Rewrite a written ORFS SDC's boundary delays to the die context: every port's input/output delay is referenced to
the propagated clock at a register of THIS block's tree in the same domain (-reference_pin), because the die-side
boundary register sits in the same band clock region (decision C) and is balanced to the same insertion delay.
max (setup) keeps the 0.2 T budget; min (hold) is 0: the source register's clk->q and wire are not credited."""
import re, sys
REF = {'clk': r'res_q\[0\]$_DFF_P_/CLK', 'bw_clk': r'g_bw.u_bw.active.rs_s1\[0\]$_DFF_P_/CLK'}
pat = re.compile(r'^set_(input|output)_delay ([0-9.]+) -clock \[get_clocks \{(\w+)\}\] -add_delay (\[get_ports \{[^}]*\}\])$')
out = []
for ln in open(sys.argv[1]):
    m = pat.match(ln.rstrip('\n'))
    if not m:
        out.append(ln.rstrip('\n'))
        continue
    kind, v, c, port = m.groups()
    ref = f'-reference_pin [get_pins {{{REF[c]}}}]'
    out.append(f'set_{kind}_delay {v} -max -clock [get_clocks {{{c}}}] {ref} -add_delay {port}')
    out.append(f'set_{kind}_delay 0 -min -clock [get_clocks {{{c}}}] {ref} -add_delay {port}')
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
