import json, re, sys, collections
# usage: cen_trace.py native_census.json netlist.v
cen = json.load(open(sys.argv[1])); txt = open(sys.argv[2]).read()
# parse cell instances: TYPE NAME ( .PIN(net), ... );
cells = {}
for m in re.finditer(r'^\s*(\w+)\s+(\\?\S+)\s*\((.*?)\);', txt, re.S | re.M):
    typ, name, body = m.group(1), m.group(2).lstrip('\\'), m.group(3)
    if typ in ('module', 'input', 'output', 'wire', 'assign'): continue
    pins = dict(re.findall(r'\.(\w+)\(\s*(\\?[^\s\)]+(?:\s*\[\d+\])?)\s*\)', body))
    cells[name] = (typ, {k: v.lstrip('\\').replace(' ', '') for k, v in pins.items()})
drv = {}
for n, (t, p) in cells.items():
    for pin, net in p.items():
        if pin in ('Y', 'QN', 'Q', 'CON', 'SN'): drv[net] = (n, pin)
def cone(net, depth=5, seen=None):
    seen = seen if seen is not None else set(); out = set()
    if depth == 0 or net in seen: return out
    seen.add(net)
    if net not in drv: out.add('PORT:' + net); return out
    c, pin = drv[net]; t, p = cells[c]
    if 'DFF' in t or '$_DFF' in c or 'DHL' in t:
        out.add(c.split('$')[0]); return out
    for k, v in p.items():
        if k not in ('Y',): out |= cone(v, depth - 1, seen)
    return out
for v in sorted(cen['violations'], key=lambda x: -x['loads']):
    d = v['driver'].split('/')[0]
    if v['driver_role'] == 'sequential': 
        print(v['loads'], 'SEQ', d); continue
    t, p = cells.get(d, ('?', {}))
    srcs = set()
    for k, n in p.items():
        if k != 'Y': srcs |= cone(n)
    print(v['loads'], 'COMB', t, sorted(srcs)[:8])
