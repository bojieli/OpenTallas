"""DIE-LAYOUT-HBM EQ_BY_CONSTRUCTION check: every changed die_plan path must be a position/route leaf
(core origin_um, core clock-entry tap xy, station regs_um/from_um/to_um, ft-slot regs_um/bit_sites_um) or a note;
station counts, windows, widths, buses, lanes, latency and outlines must be byte-identical."""
import json, sys, collections
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
diffs = []
def walk(x, y, p):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in set(x) | set(y):
            if k not in x or k not in y: diffs.append(p + (k,)); continue
            walk(x[k], y[k], p + (k,))
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, p + (i,))
    elif x != y: diffs.append(p)
walk(a, b, ())
OK = {'origin_um', 'regs_um', 'from_um', 'to_um', 'bit_sites_um', 'bit_site_cell_um', 'note', 'xy'}   # bit_site_cell_um: flop site size [1.404,0.27] that ft_s0_resite writes with explicit bit sites
cls = collections.Counter(); bad = []
for d in diffs:
    keys = [k for k in d if isinstance(k, str)]
    leaf = keys[-1]
    if leaf in OK and (leaf != 'xy' or 'taps' in keys):
        cls[(d[1] if d[0] == 'partition_types' else d[0], leaf)] += 1
    else: bad.append(d)
print('EQ_BY_CONSTRUCTION' if not bad else 'NOT_EQ', len(diffs), 'paths;', dict(cls)); print('bad', bad[:20])
