"""Independent NUMBER-CHECK of R30 FT-island legalization (written from scratch; does not use check_leg.py/legalize_isl.py).
usage: python3 numcheck_leg_r30.py BEFORE.json AFTER.json LEDGER.json OUT.json"""
import json, sys, math, hashlib
from collections import defaultdict
B_PATH, A_PATH, L_PATH, OUT = sys.argv[1:5]
pb = json.load(open(B_PATH)); pa = json.load(open(A_PATH)); led = json.load(open(L_PATH))
EPS = 1e-6; ROW = 0.27; SITE = 0.054; LIM = 405.0
R = {}

# ---------- (a) full structural diff ----------
diffs = []
def walk(a, b, path):
    if type(a) != type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        diffs.append((path, 'type')); return
    if isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b: diffs.append((path + (k,), 'key-missing'))
            else: walk(a[k], b[k], path + (k,))
    elif isinstance(a, list):
        if len(a) != len(b): diffs.append((path, 'len')); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, path + (i,))
    elif a != b: diffs.append((path, (a, b)))
walk(pb, pa, ())
cellset = set(); other = []
for path, d in diffs:
    # expected form: partition_types,cls,ft_slots,si,bit_sites_um,bank,bit,coord
    if len(path) == 8 and path[0] == 'partition_types' and path[2] == 'ft_slots' and path[4] == 'bit_sites_um':
        cellset.add((path[1], path[3], path[5], path[6]))
    else: other.append([list(map(str, path)), str(d)[:120]])
ledset = {}
for m in led['move_list']:
    si = [i for i, s in enumerate(pb['partition_types'][m['cls']]['ft_slots']) if s['name'] == m['slot']]
    assert len(si) == 1
    ledset[(m['cls'], si[0], m['bank'] - 1, m['bit'])] = m
frm_ok = to_ok = disp_ok = 0; disps = []
for (c, si, j, i), m in ledset.items():
    b = pb['partition_types'][c]['ft_slots'][si]['bit_sites_um'][j][i]
    a = pa['partition_types'][c]['ft_slots'][si]['bit_sites_um'][j][i]
    frm_ok += abs(b[0]-m['frm'][0]) < EPS and abs(b[1]-m['frm'][1]) < EPS
    to_ok += abs(a[0]-m['to'][0]) < EPS and abs(a[1]-m['to'][1]) < EPS
    d = abs(a[0]-b[0]) + abs(a[1]-b[1]); disps.append(round(d, 4))
    disp_ok += abs(d - m['disp_um']) < 1e-3
R['a'] = dict(diff_leaf_count=len(diffs), changed_ft_cells=len(cellset), ledger_moves=len(led['move_list']),
              ledger_unique=len(ledset), changed_not_in_ledger=len(cellset - set(ledset)), ledger_not_changed=len(set(ledset) - cellset),
              other_diffs=other[:20], other_diff_count=len(other), ledger_frm_match=frm_ok, ledger_to_match=to_ok, ledger_disp_match=disp_ok,
              ledger_plan_sha_matches_after=hashlib.sha256(open(A_PATH, 'rb').read()).hexdigest() == led.get('plan_sha256'),
              before_sha256=hashlib.sha256(open(B_PATH, 'rb').read()).hexdigest(), after_sha256=hashlib.sha256(open(A_PATH, 'rb').read()).hexdigest())
# ---------- (b) displacement ----------
from collections import Counter
R['b'] = dict(max_disp_um=max(disps), n_at_max=sum(1 for d in disps if abs(d-max(disps)) < 1e-3),
              hist=dict(sorted(Counter(disps).items())), ledger_max_disp=led.get('max_disp_um'))

# ---------- geometry helpers ----------
def ov(r, s):  # positive-area overlap of [x0,y0,x1,y1]
    return r[0] < s[2]-EPS and r[2] > s[0]+EPS and r[1] < s[3]-EPS and r[3] > s[1]+EPS
def macro_boxes(t):  # re-derived (same semantics as schema: hard_cores win; contents with lef; core track offset)
    ent = {c['inst']: ('core', c) for c in t.get('hard_cores') or []}
    for c in t.get('contents') or []:
        if c.get('lef') and c['inst'] not in ent: ent[c['inst']] = ('cont', c)
    out = []
    for n, (kind, c) in ent.items():
        x, y = c['origin_um']; w, h = c['outline_um']
        dx, dy = c.get('track_offset_um', [0, 0]) if kind == 'core' else (0, 0)
        out.append((x+dx, y+dy, x+dx+w, y+dy+h))
    return out
def cells(t):
    for si, s in enumerate(t['ft_slots']):
        cw, ch = s.get('bit_site_cell_um', [1.404, 0.27])
        for j, bank in enumerate(s.get('bit_sites_um') or []):
            for i, (x, y) in enumerate(bank):
                yield (si, j, i), (x, y, x+cw, y+ch)
def ongrid(v, g): return abs(v/g - round(v/g)) < 1e-4

def geom(p, moved_keys):
    res = dict(isl_hits=0, macro_hits=0, any_hits=0, ft_ft_overlap_pairs=0, out_of_outline=0, off_row=0, off_site=0, total_cells=0,
               moved=dict(isl_hits=0, macro_hits=0, ft_overlap=0, out_of_outline=0, off_row=0, off_site=0, n=0,
                          near_clock_tap_lt_8p64=0, min_dist_to_point_mech_um=None, point_mech_hits=0),
               hit_by_type={})
    mind = math.inf
    for c, t in p['partition_types'].items():
        W, H = t['outline_um']; isl = (t.get('clock') or {}).get('die_islands_um') or []; mb = macro_boxes(t)
        pts = [tuple(tp['xy']) for tp in (t.get('clock') or {}).get('taps') or []]
        tap_pts = list(pts)
        for key in ('tap_um',):
            if (t.get('clock') or {}).get(key): pts.append(tuple(t['clock'][key]))
            if (t.get('reset') or {}).get(key): pts.append(tuple(t['reset'][key]))
        lc = (t.get('clock') or {}).get('landing_contract') or {}
        pts += [tuple(q['xy_um']) for q in lc.get('pins', []) if 'xy_um' in q]
        for st in t.get('internal_stations') or []: pts += [tuple(r) for r in st.get('regs_um', [])]
        bins = defaultdict(list); hits = 0
        for k, r in cells(t):
            res['total_cells'] += 1; mv = (c,) + k in moved_keys
            hi = any(ov(r, s) for s in isl); hm = any(ov(r, s) for s in mb)
            oo = r[0] < -EPS or r[1] < -EPS or r[2] > W+EPS or r[3] > H+EPS
            orow = not ongrid(r[1], ROW); osite = not ongrid(r[0], SITE)
            res['isl_hits'] += hi; res['macro_hits'] += hm; res['any_hits'] += (hi or hm); hits += (hi or hm)
            res['out_of_outline'] += oo; res['off_row'] += orow; res['off_site'] += osite
            if mv:
                M = res['moved']; M['n'] += 1; M['isl_hits'] += hi; M['macro_hits'] += hm; M['out_of_outline'] += oo
                M['off_row'] += orow; M['off_site'] += osite
                for (px, py) in pts:
                    if r[0]-EPS <= px <= r[2]+EPS and r[1]-EPS <= py <= r[3]+EPS: M['point_mech_hits'] += 1
                    dx = max(r[0]-px, 0, px-r[2]); dy = max(r[1]-py, 0, py-r[3]); mind = min(mind, dx+dy)
                for (px, py) in tap_pts:
                    dx = max(r[0]-px, 0, px-r[2]); dy = max(r[1]-py, 0, py-r[3])
                    if max(dx, dy) < 8.64: M['near_clock_tap_lt_8p64'] += 1
            for b in range(math.floor(r[1]/ROW+1e-4), math.ceil(r[3]/ROW-1e-4)):
                bins[b].append((r, mv))
        if hits: res['hit_by_type'][c] = hits
        for lst in bins.values():   # 2-D sweep per row bin
            lst.sort(key=lambda e: e[0][0]); act = []
            for r, mv in lst:
                act = [a for a in act if a[0][2] > r[0]+EPS]
                for a, amv in act:
                    if ov(a, r):
                        res['ft_ft_overlap_pairs'] += 1
                        if mv or amv: res['moved']['ft_overlap'] += 1
                act.append((r, mv))
    res['moved']['min_dist_to_point_mech_um'] = None if mind == math.inf else round(mind, 3)
    return res
moved = set(ledset)
moved_named = {(c, si, j, i) for (c, si, j, i) in moved}
R['geom_before'] = geom(pb, moved_named); R['geom_after'] = geom(pa, moved_named)
# other-mechanism keys anywhere in the plan
kw = ('keepout', 'blockage', 'bay', 'halo', 'obstruct', 'repeater', 'exclusion')
found = set()
def kscan(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if any(w in k.lower() for w in kw): found.add('/'.join(map(str, path[:1])) + '..' + k)
            kscan(v, path + [k])
    elif isinstance(o, list):
        for v in o[:50]: kscan(v, path)
kscan(pa, []); R['other_mechanism_keys'] = sorted(found)[:30]

# ---------- (e) hops ----------
def face_pt(face, W, H, u):
    return {'N': (u, H), 'S': (u, 0.0), 'E': (W, u), 'W': (0.0, u)}[face]
def man(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def hops(p, c, si, moved_bits):
    t = p['partition_types'][c]; s = t['ft_slots'][si]; W, H = t['outline_um']; Bk = s['bit_sites_um']; n = len(Bk[0])
    regs = s.get('regs_um') or []
    assert len(regs) == len(Bk) + 1 == s['stations'], (c, s['name'])
    lo, hi = s['out_window_um']; rev = s.get('order') == 'lsb_high'
    inpt = tuple(regs[0]); half = (hi - lo) / 2
    o = dict(bank_bank_all=0, bank_bank_moved=0, in_centroid=0, in_spread=0, out_linear=0, out_far=0, out_near=0, worst_where=None)
    for i in range(n):
        for j in range(len(Bk) - 1):
            d = man(Bk[j][i], Bk[j+1][i])
            if d > o['bank_bank_all']: o['bank_bank_all'] = d; o['worst_where'] = (j, j+1, i)
            if (j, i) in moved_bits or (j+1, i) in moved_bits: o['bank_bank_moved'] = max(o['bank_bank_moved'], d)
        b0 = Bk[0][i]; bl = Bk[-1][i]
        o['in_centroid'] = max(o['in_centroid'], man(inpt, b0))
        # spread in-pin over same width as out window, centred on centroid, both bit orders (pessimistic)
        u0 = inpt[1] if s['in_face'] in 'EW' else inpt[0]
        f = (i + 0.5) / n
        for uu in (u0 - half + f*2*half, u0 + half - f*2*half):
            o['in_spread'] = max(o['in_spread'], man(face_pt(s['in_face'], W, H, uu), b0))
        uo = (hi - f*(hi-lo)) if rev else (lo + f*(hi-lo))
        o['out_linear'] = max(o['out_linear'], man(face_pt(s['out_face'], W, H, uo), bl))
        o['out_far'] = max(o['out_far'], max(man(face_pt(s['out_face'], W, H, lo), bl), man(face_pt(s['out_face'], W, H, hi), bl)))
        nu = min(max(bl[0] if s['out_face'] in 'NS' else bl[1], lo), hi)
        o['out_near'] = max(o['out_near'], man(face_pt(s['out_face'], W, H, nu), bl))
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()}
slots = defaultdict(set)
for (c, si, j, i) in moved: slots[(c, si)].add((j, i))
E = {}
for (c, si), mb in sorted(slots.items()):
    hb = hops(pb, c, si, mb); ha = hops(pa, c, si, mb)
    E[f"{c}/{pb['partition_types'][c]['ft_slots'][si]['name']}"] = dict(before=hb, after=ha, n_moved=len(mb))
def mx(side, key): return max(v[side][key] for v in E.values())
keys = ('bank_bank_all', 'bank_bank_moved', 'in_centroid', 'in_spread', 'out_linear', 'out_near', 'out_far')
R['e'] = dict(summary={k: dict(before=mx('before', k), after=mx('after', k)) for k in keys},
              slots_where_any_metric_grew=[s for s, v in E.items() if any(v['after'][k] > v['before'][k] + 1e-6 for k in keys)],
              per_slot=E, limit_um=LIM)
json.dump(R, open(OUT, 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if k != 'e'}, default=str)[:6000]); print(json.dumps(R['e']['summary'])); print(R['e']['slots_where_any_metric_grew'])
