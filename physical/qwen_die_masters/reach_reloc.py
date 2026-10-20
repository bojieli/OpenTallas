# reach_reloc.py (QW-N59SVC 2026-10-20): register-stage reach repair after global placement, 0 added cycles.
# usage: openroad -python -exit reach_reloc.py IN.odb OUT.tsv SUMMARY.json PLATFORM_DIR [REACH_UM] [PASSES]
# Builds the actual stage graph (same model as results/arch/qw_n59_svc_stage_geometry_0720/stage_graph.py: every
# combinational Liberty function collapsed from FF/macro/input to FF/macro/output; clock pins excluded, async reset pins
# kept), then moves every standard-cell register whose longest stage endpoint span exceeds REACH (L1, um) to the L1
# minimax centre of its stage neighbours (fan-in sources and fan-out endpoints), so an existing register becomes a
# forwarded hop between its neighbours (a pin register leaves its pin when its pin wire + core span cannot both fit).
# Ports, macros and FIXED cells never move.  Coordinate descent, PASSES rounds.  Writes "inst x_ll y_ll" for moved cells
# (DPL legalises them next); SUMMARY has the >REACH edge counts before / after and the residual worst edges.
import odb, sys, json, re, gzip, collections
from pathlib import Path
src, out, summ, pdir = sys.argv[1:5]
REACH = float(sys.argv[5]) if len(sys.argv) > 5 else 390.0
PASSES = int(sys.argv[6]) if len(sys.argv) > 6 else 8
db = odb.dbDatabase.create(); odb.read_db(db, src); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
def blocks(s, k):
    for m in re.finditer(r'\b' + k + r'\s*\(([^)]*)\)\s*\{', s):
        a = i = m.end(); d = 1
        while d:
            d += (s[i] == '{') - (s[i] == '}'); i += 1
        yield m[1].strip('" '), s[a:i - 1]
roles = {}
for p in Path(pdir).rglob('*.lib*'):
    if not re.search(r'_(TT|tt)', p.name): continue
    text = gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text()
    for mn, body in blocks(text, 'cell'):
        if mn in roles: continue
        pins = {}
        for pn, pb in blocks(body, 'pin'):
            di = re.search(r'\bdirection\s*:\s*(\w+)', pb); fn = re.search(r'\bfunction\s*:\s*"([^"]+)"', pb)
            pins[pn] = {'direction': di[1] if di else None, 'function': fn[1] if fn else None,
                        'clock': bool(re.search(r'\bclock\s*:\s*true', pb))}
        roles[mn] = {'pins': pins, 'seq': bool(re.search(r'\b(ff|latch)\s*\(', body))}
core = b.getCoreArea(); cx0, cy0, cx1, cy1 = core.xMin() / u, core.yMin() / u, core.xMax() / u, core.yMax() / u
def ctr(bb): return ((bb.xMin() + bb.xMax()) / 2 / u, (bb.yMin() + bb.yMax()) / 2 / u)
nodes = {}; drivers = collections.defaultdict(list); targets = []; insts = {}; unknown = set()
for i in b.getInsts():
    m = i.getMaster(); mn = m.getName(); macro = m.isBlock(); role = roles.get(mn)
    if not macro and not role:
        unknown.add(mn)
    seq = bool(role and role['seq']); kind = 'macro' if macro else ('seq' if seq else 'comb')
    ip = {p.getMTerm().getName(): p for p in i.getITerms() if str(p.getSigType()) not in ('POWER', 'GROUND')}
    movable = kind == 'seq' and str(i.getPlacementStatus()) not in ('FIRM', 'LOCKED', 'COVER')
    insts[i.getName()] = {'inst': i, 'kind': kind, 'movable': movable, 'c': ctr(i.getBBox())}
    for pn, p in ip.items():
        if not p.getNet(): continue
        di = str(p.getIoType()); pr = (role or {}).get('pins', {}).get(pn, {})
        clock = str(p.getSigType()) == 'CLOCK' or pr.get('clock')
        key = i.getName() + '/' + pn
        nodes[key] = {'inst': i.getName(), 'kind': kind, 'net': p.getNet().getId(), 'clock': bool(clock)}
        if di == 'OUTPUT':
            deps = []
            if kind == 'comb':
                fn = pr.get('function')
                ins = [(qn, q) for qn, q in ip.items() if q.getNet() and str(q.getIoType()) == 'INPUT']
                if fn is None:
                    deps = [q.getNet().getId() for qn, q in ins]   # unknown function: every input (superset)
                else:
                    deps = [q.getNet().getId() for qn, q in ins
                            if re.search(r'(?<![A-Za-z0-9_])' + re.escape(qn) + r'(?![A-Za-z0-9_])', fn)]
            drivers[p.getNet().getId()].append((key, deps))
        elif di == 'INPUT' and kind in ('seq', 'macro') and not clock:
            targets.append(key)
ports = {}
for p in b.getBTerms():
    if str(p.getSigType()) in ('POWER', 'GROUND') or not p.getNet(): continue
    key = 'PORT/' + p.getName(); di = str(p.getIoType())
    ports[key] = ctr(p.getBBox())
    nodes[key] = {'inst': key, 'kind': 'port', 'net': p.getNet().getId(), 'clock': str(p.getSigType()) == 'CLOCK'}
    if di == 'INPUT': drivers[p.getNet().getId()].append((key, []))
    elif di == 'OUTPUT': targets.append(key)
sys.setrecursionlimit(100000)
memo = {}
def roots(net):
    if net in memo: return memo[net]
    memo[net] = frozenset()      # cycle guard
    res = set()
    for key, deps in drivers[net]:
        if nodes[key]['kind'] == 'comb':
            for d in deps: res |= roots(d)
        else: res.add(key)
    memo[net] = frozenset(res); return memo[net]
def owner(key): return nodes[key]['inst']
pos = {}
for k, v in insts.items(): pos[k] = list(v['c'])
for k, v in ports.items(): pos[k] = list(v)
nbr = collections.defaultdict(set); edges = set()
for dst in targets:
    for s in roots(nodes[dst]['net']):
        if nodes[s]['clock']: continue
        a, z = owner(s), owner(dst)
        if a == z: continue
        edges.add((a, z)); nbr[a].add(z); nbr[z].add(a)
def d1(a, z): pa, pz = pos[a], pos[z]; return abs(pa[0] - pz[0]) + abs(pa[1] - pz[1])
def census():
    over = [(d1(a, z), a, z) for a, z in edges if d1(a, z) > 405.0]
    return len(over), sorted(over, reverse=True)[:40]
before, bworst = census()
moved = {}
mov = [k for k, v in insts.items() if v['movable'] and nbr.get(k)]
for it in range(PASSES):
    n = 0
    for k in mov:
        ns = nbr[k]
        cur = max(d1(k, z) for z in ns)
        if cur <= REACH: continue
        us = [pos[z][0] + pos[z][1] for z in ns]; vs = [pos[z][0] - pos[z][1] for z in ns]
        uc = (min(us) + max(us)) / 2; vc = (min(vs) + max(vs)) / 2
        x = min(max((uc + vc) / 2, cx0 + 1), cx1 - 1); y = min(max((uc - vc) / 2, cy0 + 1), cy1 - 1)
        old = pos[k]; pos[k] = [x, y]
        new = max(d1(k, z) for z in ns)
        if new < cur - 0.5: moved[k] = (x, y); n += 1
        else: pos[k] = old
    print('RELOC pass', it, 'moved', n, flush=True)
    if n == 0: break
after, aworst = census()
with open(out, 'w') as f:
    for k, (x, y) in moved.items():
        i = insts[k]['inst']; bb = i.getBBox(); w = (bb.xMax() - bb.xMin()) / u; h = (bb.yMax() - bb.yMin()) / u
        f.write('%s %.4f %.4f\n' % (k, x - w / 2, y - h / 2))
res = {'reach_um': REACH, 'edges': len(edges), 'gt405_before': before, 'gt405_after': after, 'moved': len(moved),
       'unknown_masters': sorted(unknown)[:20], 'worst_before': bworst[:10], 'residual_after': aworst}
json.dump(res, open(summ, 'w'), indent=1)
print('RELOC_SUMMARY', json.dumps({k: res[k] for k in ('edges', 'gt405_before', 'gt405_after', 'moved')}), flush=True)
