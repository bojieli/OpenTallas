import json, sys, statistics as st, collections, math
B = sys.argv[1]; C = sys.argv[2] if len(sys.argv) > 2 else 'TT'
M = json.load(open(f'{B}/mesh.json'))
arr = {}
for l in open(f'{B}/tree_{C}.txt'):
    f = l.split()
    if len(f) >= 4: arr[f[1]] = (float(f[2]), float(f[3]), float(f[4]) if len(f) > 4 else 0)
# driver by site coordinate
dsite = {}
for k, d in M['drivers'].items():
    dsite[(round(d['site'][0], 2), round(d['site'][1], 2))] = d
node_of = {}
for h in M['htree']:
    if h.get('node'): node_of[h['tag']] = h['node']
node_of['h'] = 'ckm_n0'
rows = []
for h in M['htree']:
    par = node_of.get(h['tag'][:-1])
    if h['leaf']:
        d = dsite.get((round(h['b'][0], 2), round(h['b'][1], 2)))
        if d is None:
            rows.append(dict(h, par=par, end=None, dly=None)); continue
        end = d['cells'][0]
    else:
        end = h['node']
    if par not in arr or end not in arr:
        rows.append(dict(h, par=par, end=end, dly=None)); continue
    rows.append(dict(h, par=par, end=end, dly=arr[end][0] - arr[par][0], slew=arr[end][2]))
json.dump([{k: r[k] for k in ('level', 'tag', 'len_um', 'n_seg', 'par', 'end', 'dly', 'leaf') if k in r} | {'slew': r.get('slew'), 'nrep': len(r['reps'])} for r in rows], open(f'/tmp/pd10_legs_{C}.json', 'w'))
by = collections.defaultdict(list)
for r in rows:
    if r['dly'] is not None: by[r['level']].append(r)
print('missing', sum(r['dly'] is None for r in rows))
for L in sorted(by):
    R = by[L]; d = [r['dly'] for r in R]; ln = [r['len_um'] for r in R]; ns = collections.Counter(r['n_seg'] for r in R)
    print(f"L{L:2d} n={len(R):4d} dly {min(d):7.1f}-{max(d):7.1f} sd {st.pstdev(d):5.1f}  len {min(ln):7.1f}-{max(ln):7.1f}  nseg {dict(ns)}")
