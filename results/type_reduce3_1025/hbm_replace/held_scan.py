#!/usr/bin/env python3
"""TYPE-REDUCE-3 10-25: why do the HBM held groups (TYPE-REDUCE-2 face_defer.json) need several pin tables?
Per held module: members (type, inst, origin in parent, parent outline), per-bus dominant face of each member's own
pin table, face classes exact vs modulo whole-instance orient (R0/MX/MY/R180), and the best one-table+orient
displacement (pins > 405 um).  Read-only on B2n (claude/type-reduce2-hbm-1025 plan). Run from the repo root."""
import collections, json, re, sys
P = 'physical/die_plan/hbm_arch/B2n'
plan = json.load(open(f'{P}/die_plan.json'))
held = json.load(open('results/type_reduce2_hbm_1025/face_defer.json'))
T = plan['partition_types']
ninst = collections.Counter(p['type'] for p in plan['partitions'])
OR = ('R0', 'MX', 'MY', 'R180')
FMAP = {'R0': {}, 'MY': {'E': 'W', 'W': 'E'}, 'MX': {'N': 'S', 'S': 'N'}, 'R180': {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}}
def xf(o, w, h, x, y):
    if o in ('MY', 'R180'): x = w - x
    if o in ('MX', 'R180'): y = h - y
    return x, y
def bus(n):
    return re.sub(r'\[\d+\]$', '', n)
def load(pf):
    d = json.load(open(f'{P}/{pf}'))
    d = d['pins'] if isinstance(d, dict) else d
    return {p['name']: (float(p['x']), float(p['y'])) for p in d}
out = {}
for m in held:
    mem = []
    for tn, t in sorted(T.items()):
        for hc in t.get('hard_cores') or []:
            if hc['module'] == m or (m == 'pg_pretree' and hc['module'] == 'ot_hbm_su_pg_pretree_core'):
                mem.append((tn, t, hc))
    if not mem:
        out[m] = dict(note='module not in B2n plan (alias)'); continue
    byo = collections.defaultdict(list)
    for e in mem: byo['x'.join(f'{v:g}' for v in e[2]['outline_um'])].append(e)
    for wh, ms in byo.items():
        w, h = ms[0][2]['outline_um']
        rows, tabs, sigs = [], [], []
        for tn, t, hc in ms:
            tab = load(hc['pins_file']); tabs.append(tab)
            c = collections.Counter()
            for n, (x, y) in tab.items():
                c[(bus(n), min((x, 'W'), (w - x, 'E'), (y, 'S'), (h - y, 'N'))[1])] += 1
            dom = {}
            for (b, f), k in c.items():
                if k > dom.get(b, ('', 0))[1]: dom[b] = (f, k)
            sig = {b: f for b, (f, _k) in dom.items()}; sigs.append(sig)
            ox, oy = hc['origin_um']; W, H = t['outline_um']
            rows.append(dict(type=tn, inst=hc['inst'], replicas=ninst[tn], parent=f'{W:g}x{H:g}',
                             at=[round(ox, 1), round(oy, 1)], rel=[round((ox + w / 2) / W, 2), round((oy + h / 2) / H, 2)],
                             faces=dict(collections.Counter(sig.values()))))
        names = [frozenset(t) for t in tabs]
        exact = len({json.dumps(sorted(s.items())) for s in sigs})
        # classes modulo orient: member j joins class of i if some orient maps sig_j onto sig_i
        cls = []
        for j, s in enumerate(sigs):
            for c in cls:
                s0 = sigs[c[0]]
                if set(s) == set(s0) and any(all(FMAP[o].get(s[b], s[b]) == s0[b] for b in s) for o in OR):
                    c.append(j); break
            else: cls.append([j])
        # best one table (each member's own table as candidate) + per-member best orient: pins > 405
        best = None
        if len(set(names)) == 1:
            for k, tk in enumerate(tabs):
                far = 0; worst = 0; oris = []
                for tab in tabs:
                    r = []
                    for o in OR:
                        d = [abs(x - xf(o, w, h, *tk[n])[0]) + abs(y - xf(o, w, h, *tk[n])[1]) for n, (x, y) in tab.items()]
                        r.append((sum(1 for v in d if v > 405), max(d), o))
                    f, mx, o = min(r); far += f; worst = max(worst, mx); oris.append(o)
                if best is None or far < best[0]: best = (far, round(worst, 1), k, oris)
        out[f'{m}|{wh}'] = dict(members=len(ms), replicas=sum(r['replicas'] for r in rows), tables=len({json.dumps(sorted(t.items())) for t in tabs}),
                                same_pin_names=len(set(names)) == 1, face_classes_exact=exact, face_classes_mod_orient=len(cls),
                                classes=[[rows[j]['type'] + '/' + rows[j]['inst'] for j in c] for c in cls],
                                best_one_table=None if best is None else dict(pins_over_405=best[0], max_um=best[1], template=rows[best[2]]['type'] + '/' + rows[best[2]]['inst'], orients=best[3]),
                                rows=rows)
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else '/dev/stdout', 'w'), indent=1)
