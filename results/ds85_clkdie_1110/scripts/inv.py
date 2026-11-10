import json, re, glob, collections, os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(f'{B}/wt/physical/die_plan/s81/plan_h2_2249.json'))
P = {p['name']: p for p in d['partitions']}
E = [e for e in d['clock']['landing_network']['edges'] if e['kind'] == 'clock']
need = collections.Counter()
for e in E:
    need[P[e['src']['part']]['type']] += 1
    need[P[e['dst']['part']]['type']] += 1
print('clock edges', len(E), 'types involved', len(need))
# signed views of plan_h2_2249 (release cache)
cache = json.load(open(os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json')))
st = cache['plans']['s81/plan_h2_2249.json']['signed_types']
signed = {}
for ty, recs in st.items():
    for r in recs:
        m = re.match(r'(\S+?):(\S+) src (\S+) flow (\S+) (.*?) db (\S+)', r)
        if m:
            signed.setdefault(ty, (m.group(1), m.group(6), m.group(2), m.group(4)))
best = {}
for f in glob.glob(f'{B}/inv/odb_*.txt'):
    h = f.split('odb_')[1][:-4]
    for ln in open(f):
        x = ln.split(' ', 2)
        if len(x) < 3:
            continue
        try:
            t, s, p = float(x[0]), int(x[1]), x[2].strip()
        except ValueError:
            continue
        m = re.search(r'/results/asap7/([^/]+)/base/6_final\.odb$', p)
        if not m:
            continue
        cands = [re.sub(r'^(dp_|kl_|s81p_)', '', m.group(1))]
        m2 = re.search(r'/items/([^/]+)/attempt_', p)
        if m2:
            cands.insert(0, m2.group(1))
        ty = next((c for c in cands if c in need), None)
        if ty is None:
            continue
        if ty not in best or t > best[ty][0]:
            best[ty] = (t, h, p, s)
sel = {}
for ty in need:
    if ty in signed:
        h, db, so, flow = signed[ty]
        sel[ty] = dict(kind='SIGNED', host=h, odb=db, signoff=so, flow=flow)
    elif ty in best:
        t, h, p, s = best[ty]
        sel[ty] = dict(kind='ROUTED_UNSIGNED', host=h, odb=p, mtime=t)
print('signed', sum(1 for v in sel.values() if v['kind'] == 'SIGNED'), 'routed-unsigned',
      sum(1 for v in sel.values() if v['kind'] != 'SIGNED'), 'none', len(set(need) - set(sel)))
json.dump(dict(selection=sel, none=sorted(set(need) - set(sel)), need=dict(need)), open(f'{B}/inv/type_select.json', 'w'), indent=1)
print('none:', sorted(set(need) - set(sel)))
