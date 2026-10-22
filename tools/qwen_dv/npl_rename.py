#!/usr/bin/env python3
"""QE3-CTLM3 10-21: lp9d_np -> lp9d_npl transform as a tool (QW-TTC9 did it by hand, 2ff3ed160 / 50cbdca4a / 34165544b):
(1) landing-ring cells get their ring instance names back (u_<i> whose construct source cell is u_lpl_<n>_<w|r>.* ->
\\u_lpl_<n>_<w|r>.u<i>), so lp.py's L5 ring -> read multicycles bind; (2) 1-bit ports declared scalar (lp8_np form);
(3) the sim-only ROM266 INSTANCE strings dropped (the kit binds the calendar images by instance path).  Logic unchanged.
usage: npl_rename.py NP_NETLIST NAMEMAP_JSON OUT"""
import re, sys, json
src, nm, out = sys.argv[1:4]
names = json.load(open(nm))['names']
text = open(src).read()
lpl = re.compile(r'^(u_lpl_\d+_[wr])\.')
def ren(m):
    i = int(m.group(2)); g = lpl.match(names[i]) if i < len(names) else None
    return f'{m.group(1)}\\{g.group(1)}.u{i} (' if g else m.group(0)
text = re.sub(r'(\) )u_(\d+)\(', ren, text)
text = re.sub(r'^(input|output) wire \[0:0\] ', r'\1 wire ', text, flags=re.M)
text = re.sub(r'(ot_rom_4096x266_m8) #\(\.INSTANCE\("[^"]*"\)\) ', r'\1 ', text)
open(out, 'w').write(text)
