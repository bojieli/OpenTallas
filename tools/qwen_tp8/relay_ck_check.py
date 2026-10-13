#!/usr/bin/env python3
"""Every relay / station instance of a die case netlist has its clock pin connected (main 758ccc84c: KV relays had none,
so die STA timed no relay hop).  usage: relay_ck_check.py CASE/die.v  -> prints counts, exit 1 on any unclocked relay"""
import re, sys, collections
txt = open(sys.argv[1]).read()
inst = re.compile(r'\n\s*(q[fk]d_(?:rly|stn|station)\w*)\s+\\?(\S+)\s*\((.*?)\);', re.S)
n, bad, by = 0, [], collections.Counter()
for mst, name, body in inst.findall(txt):
    n += 1
    ck = re.search(r'\.(ck|clk|clk_i)\s*\(\s*([^)\s]*)\s*\)', body)
    if not ck or not ck.group(2):
        bad.append(name); by[mst.split('_')[0] + '_' + mst.split('_')[1]] += 1
print(f'relays/stations {n}, unclocked {len(bad)}', dict(by), bad[:8])
sys.exit(1 if bad or not n else 0)
