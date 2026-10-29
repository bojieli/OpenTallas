"""DIE-QC-35 WHAT-IF (estimate before build, NOT a build): de-stack clock cells whose A/Y pins share an M7
column (|dx|<=.064 um) with another clock net's pin within DY um, by whole-site x shifts, then run the same
fixed_tree_provider prebuild. Placement legality vs non-clock cells is NOT checked (what-if only)."""
import sys, json, collections, math, re
src, rep = sys.argv[1], sys.argv[2]; DY = float(sys.argv[3]); argv = sys.argv[4:]
sys.path.insert(0, src+'/tools/die_plan'); sys.path.insert(0, src+'/tools/clk')
import fixed_tree_provider as F
orig_exec = exec
def hook(ns):
    cg = ns['clock_graph']; la = ns['lef_access']
    def clock_graph(text, tree):
        cells, nets = cg(text, tree)
        lef = open(ns['_lef_path']).read()
        acc = {m: la(lef, m)[1] for m in {c['lib'] for c in cells.values()}}
        pinnet = {}
        for n in nets:
            if not n['drv'].startswith('port:'): pinnet[(n['drv'], 'Y')] = n['name']
            for ld in n['loads']:
                if not ld.startswith('port:'): pinnet[(ld, 'A')] = n['name']
        B = .2; bins = collections.defaultdict(list); shifted = {}; fails = 0
        order = sorted(cells, key=lambda k: (cells[k]['x'], cells[k]['y']))
        def pins(name, x):
            c = cells[name]; return [(x+acc[c['lib']][p][0], c['y']+.135, pinnet.get((name, p))) for p in ('A', 'Y')]
        def bad(name, x):
            for px, py, net in pins(name, x):
                for b in range(math.floor((px-.07)/B), math.floor((px+.07)/B)+1):
                    for ox, oy, onet, other in bins[b]:
                        if other != name and onet != net and abs(ox-px) <= .064+1e-9 and abs(oy-py) < DY: return True
            return False
        for name in order:
            x0 = cells[name]['x']; chosen = None
            for s in (0, 2, -2, 4, -4, 6, -6, 8, -8, 10, -10, 12, -12):
                if not bad(name, round(x0+s*.054, 6)): chosen = s; break
            if chosen is None: chosen = 0; fails += 1
            if chosen: shifted[name] = chosen; cells[name]['x'] = round(x0+chosen*.054, 6)
            for px, py, net in pins(name, cells[name]['x']): bins[math.floor(px/B)].append((px, py, net, name))
        json.dump(dict(dy_um=DY, cells=len(cells), shifted=len(shifted), unresolved=fails,
                       shift_sites_hist=collections.Counter(shifted.values()), max_abs_um=max([abs(v)*.054 for v in shifted.values()] or [0])),
                  open(rep, 'w'), indent=1)
        print('WHATIF destack', len(shifted), 'shifted', fails, 'unresolved', flush=True)
        return cells, nets
    ns['clock_graph'] = clock_graph
# patch F.main's exec usage: wrap compile+exec via builtins
import builtins
real_exec = builtins.exec
def ex(code, g=None, l=None):
    r = real_exec(code, g) if l is None else real_exec(code, g, l)
    if isinstance(g, dict) and 'clock_graph' in g and '_provider_loads' in g and not g.get('_dq35'):
        g['_dq35'] = 1; hook(g)
    return r
builtins.exec = ex
lefp = argv[argv.index('--lef')+1]
F_main_ns_lef = lefp
_old = F.main
import types
def main(a):
    # stash lef path for the hook
    builtins._dq35_lef = lefp
    return _old(a)
F.json = F.json
orig_hook = hook
def hook2(ns):
    ns['_lef_path'] = lefp; orig_hook(ns)
hook = hook2
main(argv)
