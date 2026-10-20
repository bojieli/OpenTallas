import sys, json, collections, importlib.util
WT = sys.argv[1]
spec = importlib.util.spec_from_file_location('tc', WT + '/tools/toksim_s81_compose.py')
tc = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc)
paths = {}
orig = tc.solve
def solve(dag, cyc):
    T, p = orig(dag, cyc)
    paths[dag.get('mode')] = (dag, cyc, p)
    return T, p
tc.solve = solve
r = tc.build(tc.OUT / 'elements')
for wl, (dag, cyc, path) in paths.items():
    crit = [n['id'] for n in dag['nodes'] if n.get('critical')]
    N = {n['id']: n for n in dag['nodes']}
    a, b = set(crit) - set(path), set(path) - set(crit)
    ca = collections.Counter(); cb = collections.Counter()
    for i in a: ca[(N[i].get('cls'), N[i].get('op'))] += cyc[i]
    for i in b: cb[(N[i].get('cls'), N[i].get('op'))] += cyc[i]
    print('==', wl, 'T', r['workloads'][wl]['T_cycles'], 'crit-only', round(sum(ca.values())), 'solved-only', round(sum(cb.values())))
    print('  dropped from path:', [(k, round(v)) for k, v in ca.most_common(12)])
    print('  added to path    :', [(k, round(v)) for k, v in cb.most_common(12)])
    # per-layer where they differ
    lay = collections.Counter(N[i].get('group') for i in b)
    print('  added groups', lay.most_common(10))
