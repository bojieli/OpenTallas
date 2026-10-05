#!/usr/bin/env python3
"""Group the top reg-to-reg endpoints of a screen log (OT_TOP block) by register name."""
import collections, re, sys
txt = open(sys.argv[1]).read()
blk = re.search(r"OT_TOP_BEGIN\n(.*?)OT_TOP_END", txt, re.S).group(1)
g = collections.defaultdict(list)
for line in blk.splitlines():
    f = line.split()
    if len(f) >= 5 and f[-1].lstrip('-').replace('.', '').isdigit():
        g[re.sub(r"\[\d+\]|\$.*", "", f[2])].append((float(f[-1]), re.sub(r"\$.*", "", f[0])))
for k, v in sorted(g.items(), key=lambda kv: min(kv[1]))[:int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
    w = min(v)
    print("%-30s n=%3d worst %7.1f from %s" % (k, len(v), w[0], w[1]))
