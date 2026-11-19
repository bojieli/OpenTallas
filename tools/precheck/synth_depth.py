#!/usr/bin/env python3
"""synth_depth.py NETLIST.v [MODULE_REGEX] [END_REGEX]: gate depth (cells, buffers/inverters counted apart) into every flop D of the
matching modules of a yosys gate netlist; prints the histogram and the deepest ends whose instance name matches END_REGEX."""
import re, sys, collections
src = open(sys.argv[1]).read()
mre = re.compile(sys.argv[2]) if len(sys.argv) > 2 else re.compile('.')
ere = re.compile(sys.argv[3]) if len(sys.argv) > 3 else re.compile('.')
OUT = {'Y', 'Q', 'QN', 'CON', 'SN', 'CO', 'S'}
for mm in re.finditer(r'\bmodule\s+(\S+)\s*\((.*?)\bendmodule', src, re.S):
    name, body = mm.group(1), mm.group(2)
    if not mre.search(name): continue
    drv = {}; cells = []
    for cm in re.finditer(r'^\s*([A-Za-z0-9_]+_ASAP7_75t_\w+)\s+(\S+)\s*\((.*?)\);', body, re.S | re.M):
        typ, inst, pins = cm.group(1), cm.group(2), cm.group(3)
        pm = dict((p, n.strip()) for p, n in re.findall(r'\.(\w+)\(([^()]*)\)', pins))
        cells.append((typ, inst, pm))
    for i, (typ, inst, pm) in enumerate(cells):
        if typ.startswith(('DFF', 'DLL', 'DHL', 'ICG', 'SDF')): continue
        for p, n in pm.items():
            if p in OUT: drv[n] = i
    memo = {}
    def depth(n):
        st = [n]
        while st:
            x = st[-1]
            if x in memo: st.pop(); continue
            i = drv.get(x)
            if i is None: memo[x] = (0, 0); st.pop(); continue
            typ, inst, pm = cells[i]
            ins = [v for p, v in pm.items() if p not in OUT]
            need = [v for v in ins if v not in memo]
            if need: st.extend(need); continue
            b = typ.startswith(('BUF', 'INV', 'HB'))
            best = max((memo[v] for v in ins), key=lambda t: t[0] + t[1], default=(0, 0))
            memo[x] = (best[0] + (0 if b else 1), best[1] + (1 if b else 0)); st.pop()
        return memo[n]
    ends = []
    for typ, inst, pm in cells:
        if typ.startswith(('DFF', 'SDF')) and 'D' in pm and ere.search(inst):
            ends.append((depth(pm['D']), inst))
    if not ends: continue
    h = collections.Counter(min(d[0] // 4 * 4, 40) for d, _ in ends)
    ends.sort(key=lambda t: -(t[0][0] + t[0][1]))
    print(f"MODULE {name[:60]} cells {len(cells)} flop ends {len(ends)} max gates {max(d[0] for d,_ in ends)} max gates+bufs {ends[0][0][0]+ends[0][0][1]}")
    print("  gate-level histogram (bucket of 4):", dict(sorted(h.items())))
    for d, inst in ends[:6]: print(f"  {d[0]} gates + {d[1]} buf/inv  {inst[:90]}")
