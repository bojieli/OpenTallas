#!/usr/bin/env python3
"""HBM-IR8: insts.tsv (ir_drop.py format) from a die_case_v16 case dir (run.tcl place_inst + die.v masters + views/*.lef SIZE)."""
import re, sys, glob, os, collections, json
case, out = sys.argv[1], sys.argv[2]
size = {}
for f in glob.glob(os.path.join(case, 'views', '*.lef')):
    m = None
    for ln in open(f, errors='replace'):
        s = ln.split()
        if not s: continue
        if s[0] == 'MACRO': m = s[1]
        elif s[0] == 'SIZE' and m and m not in size: size[m] = (float(s[1]), float(s[3]))
master = {}
pat = re.compile(r'^\s*([A-Za-z_][\w$]*)\s+(\\?\S+)\s*\(')
for ln in open(os.path.join(case, 'die.v'), errors='replace'):
    m = pat.match(ln)
    if m and m.group(1) not in ('module', 'input', 'output', 'wire', 'inout', 'assign'):
        master[m.group(2).lstrip('\\')] = m.group(1)
die = None; rows = []; miss = collections.Counter(); kinds = collections.Counter()
pi = re.compile(r'place_inst -name (\S+) -location \{([\d.\-]+) ([\d.\-]+)\} -orientation (\S+)')
for ln in open(os.path.join(case, 'run.tcl')):
    if ln.startswith('initialize_floorplan'):
        v = re.search(r'-die_area \{([^}]*)\}', ln).group(1).split(); die = tuple(map(float, v))
    m = pi.match(ln)
    if not m: continue
    n, x, y, o = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4)
    ms = master.get(n)
    if ms not in size: miss[ms] += 1; continue
    w, h = size[ms]
    if o in ('R90', 'R270', 'MXR90', 'MYR90'): w, h = h, w
    rows.append(f'{n}\t{ms}\t{x}\t{y}\t{x+w}\t{y+h}')
    kinds[ms] += w * h
with open(out, 'w') as f:
    f.write('#die\t%s\t%s\t%s\t%s\n' % die); f.write('\n'.join(rows) + '\n')
json.dump(dict(insts=len(rows), missing=dict(miss.most_common(20)), missing_total=sum(miss.values()),
               area_mm2_by_master=dict(sorted(((k, round(v/1e6, 4)) for k, v in kinds.items()), key=lambda t: -t[1]))),
          open(out + '.census.json', 'w'), indent=1)
print('insts', len(rows), 'missing', sum(miss.values()), 'die', die)
