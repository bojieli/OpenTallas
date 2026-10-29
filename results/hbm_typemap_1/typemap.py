#!/usr/bin/env python3
# usage: typemap.py <repo> <plan commit> <out dir>/map.tsv <OWNERS.tsv>   (also writes <out dir>/kits.tsv)
"""HBM-TYPEMAP-1: hash-variant core items -> plan entries, RTL master, pin-table relation to the family reference."""
import json, subprocess, sys, re, hashlib, collections
REPO, R, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, REPO + '/tools/autopilot')
import ownership as O
P = 'physical/die_plan/hbm_arch/B2n/'
def show(p):
    return subprocess.run(['git', '-C', REPO, 'show', f'{R}:{p}'], capture_output=True, text=True, check=True).stdout
plan = json.loads(show(P + 'die_plan.json'))
canon = json.loads(show('physical/die_plan/hbm/cores/harden/canonical_ports_split.json'))
T = plan['partition_types']
ninst = collections.Counter(p['type'] for p in plan['partitions'])
hc = []
for k, v in T.items():
    for h in v.get('hard_cores') or []:
        if h.get('pins_file'):
            hc.append((k, h))
pins = {h['pins_file']: show(P + h['pins_file']) for _, h in hc}
items = O.plan_items('hbm', plan, pins, O.canonical_masters(canon))
check = {}
for cn, c in canon['types'].items():
    for tid, x in (c.get('type_ids') or {}).items():
        check[re.sub(r'__[\d.]+x[\d.]+$', '', tid)] = (c.get('top') or cn, x.get('check'), c.get('port_check'), x.get('straps') or {})
FAMS = ['idx_score_quarter', 'pc_ctrl_leaf_cfg_h9b', 'vms_bank_native_q0_faces', 'hc_root', 'vmdel_lane_n', 'sm_group_rel_id',
        'kshare_splitstrap', 'xload_cl2_bfqg', 'xload_cl2_bdring', 'xq_pegress']
owners = {}
for ln in open(sys.argv[4]):
    f = ln.rstrip('\n').split('\t')
    if len(f) > 4 and f[0] == 'hbm':
        owners[f[1]] = f[3]
cutmap = {}
for cn, c in canon['types'].items():
    for tid, x in (c.get('type_ids') or {}).items():
        cutmap[re.sub(r'__[\d.]+x[\d.]+$', '', tid)] = {b: '+'.join(sorted(m)) for b, m in (x.get('cut_pins') or {}).items()}
def table(text, module=None):
    """pin table; piece port names renamed to the canonical master's ports (canonical_ports_split cut_pins)"""
    Pn = json.loads(text)
    Pn = Pn.get('pins', []) if isinstance(Pn, dict) else Pn
    cm = cutmap.get(module) or {}
    out = {}
    for p in Pn:
        n = str(p['name'])
        m = re.match(r'^(.*?)(\[\d+\])?$', n)
        n = cm.get(m.group(1), m.group(1)) + (m.group(2) or '')
        out[n] = (str(p.get('layer')), round(float(p['x']), 3), round(float(p['y']), 3))
    return out
def base(n):
    return re.sub(r'\[\d+\]$', '', n)
def face(x, y, W, H):
    dd = {'W': x, 'E': W - x, 'S': y, 'N': H - y}
    return min(dd, key=dd.get)
def perim(x, y, W, H):
    """position along the outline perimeter (counter-clockwise from (0,0)), pin snapped to its nearest face"""
    f = face(x, y, W, H)
    return {'S': x, 'E': W + y, 'N': W + H + (W - x), 'W': 2 * W + H + (H - y)}[f]
def detour(a, b, W, H, fx):
    """parent wire added per pin if variant b used reference a's table (oriented by fx): perimeter distance"""
    L = 2 * (W + H)
    ds = []
    for n in a:
        x, y = fx(a[n][1], a[n][2])
        d = abs(perim(x, y, W, H) - perim(b[n][1], b[n][2], W, H))
        ds.append(min(d, L - d))
    ds.sort()
    return ds[-1], ds[int(0.95 * (len(ds) - 1))]
HOP_UM = 405.0      # 10-27 type-reduction limit: hops <= 405 um
def relation(a, b, W, H):
    """b relative to reference a"""
    if set(a) != set(b):
        return 'PORTSET-DIFF(%d/%d)' % (len(set(a) ^ set(b)), len(a))
    best = None
    for nm, fx in (('R0', lambda x, y: (x, y)), ('MY', lambda x, y: (round(W - x, 3), y)),
                   ('MX', lambda x, y: (x, round(H - y, 3))), ('R180', lambda x, y: (round(W - x, 3), round(H - y, 3)))):
        same = sum(1 for n in a if fx(a[n][1], a[n][2]) == (b[n][1], b[n][2]) and a[n][0] == b[n][0])
        if best is None or same > best[1]:
            best = (nm, same, fx)
    fa = collections.Counter(face(a[n][1], a[n][2], W, H) for n in a)
    fsame = sum(1 for n in a if face(a[n][1], a[n][2], W, H) == face(b[n][1], b[n][2], W, H))
    fa_b, fb_b = collections.defaultdict(set), collections.defaultdict(set)
    for n in a:
        fa_b[base(n)].add(face(a[n][1], a[n][2], W, H)); fb_b[base(n)].add(face(b[n][1], b[n][2], W, H))
    bsame = sum(1 for k in fa_b if fa_b[k] == fb_b[k])
    lay = sum(1 for n in a if a[n][0] == b[n][0])
    mx, p95 = detour(a, b, W, H, best[2])
    cls = 'COLLAPSE-CAND' if mx <= HOP_UM else 'OWN-KIT'
    return cls, round(mx), round(p95), '%s %d/%d exact; same-face pins %d/%d; same-face buses %d/%d; same-layer %d/%d' % (
        best[0], best[1], len(a), fsame, len(a), bsame, len(fa_b), lay, len(a))
rows = []
def rtl_note(it, m):
    ch = [check.get(mm) for mm in it['modules']]
    if all(c is None for c in ch):
        return 'IDENTICAL: same module %s, no per-instance params (plan hard_cores carry none)' % it['module']
    straps = sorted({json.dumps(c[3], sort_keys=True) for c in ch if c})
    return 'IDENTICAL: canonical split %s port_check %s, piece checks %s, straps %s' % (
        m.replace('core:', ''), ','.join(sorted({str(c[2]) for c in ch if c})), ','.join(sorted({str(c[1]) for c in ch if c})), '|'.join(straps))
fam_items = collections.defaultdict(list)
for it in items:
    if it['kind'] != 'core':
        continue
    fam = next((f for f in FAMS if f in it['item']), None)
    if fam:
        fam_items[fam].append(it)
for fam, its in fam_items.items():
    # instances per item
    for it in its:
        it['inst'] = [(k, h) for k, h in hc if h['module'] in it['modules']
                      and O.pin_sig(pins[h['pins_file']])[1] == it['design'].split('|')[-1]]
    # reference per RTL master: the item with the most replicas
    bym = collections.defaultdict(list)
    for it in its:
        bym[it['design'].split('|')[0]].append(it)
    for m, group in bym.items():
        W, H = group[0]['inst'][0][1]['outline_um']
        tabs = {it['item']: table(pins[it['inst'][0][1]['pins_file']], it['inst'][0][1]['module']) for it in group}
        rel = {(r['item'], it['item']): (('REFERENCE', 0, 0, 'REFERENCE') if r is it else relation(tabs[r['item']], tabs[it['item']], W, H))
               for r in group for it in group}
        # greedy cover: fewest kit references so that every variant is within the 405-um hop of one reference
        left, refs = {it['item'] for it in group}, []
        while left:
            r = max(group, key=lambda r: (sum(1 for x in left if rel[(r['item'], x)][0] != 'OWN-KIT'), r['replicas'], -len(r['item'])))
            refs.append(r)
            left -= {x for x in left if rel[(r['item'], x)][0] != 'OWN-KIT'}
        for it in group:
            ref = min(refs, key=lambda r: (rel[(r['item'], it['item'])][1], -r['replicas']))
            if it['item'] in {r['item'] for r in refs}:
                ref = it
            k0, h0 = it['inst'][0]
            r = rel[(ref['item'], it['item'])]
            rows.append(dict(item=it['item'], family=fam, state=owners.get(it['item'], '?'), rtl_master=m.replace('core:', ''),
                             outline='x'.join(map(str, h0['outline_um'])), pin_table=it['design'].split('|')[-1],
                             replicas=it['replicas'], n_pieces=len(it['members']),
                             plan_entries=';'.join(f"{k}/{h['inst']}x{ninst[k]}" for k, h in it['inst']),
                             reference=ref['item'], collapse_est=('KIT-REFERENCE' if it is ref else r[0]),
                             detour_max_um=r[1], detour_p95_um=r[2], pins_vs_reference=r[3],
                             rtl_equiv=rtl_note(it, m)))
cols = list(rows[0])
with open(OUT, 'w') as f:
    f.write('\t'.join(cols) + '\n')
    for r in sorted(rows, key=lambda r: (r['family'], r['rtl_master'], r['item'])):
        f.write('\t'.join(str(r[c]) for c in cols) + '\n')
print(len(rows), 'rows')
# distinct designs that need their own kit (one per KIT-REFERENCE) + the variants each would absorb on a plan collapse
kits = collections.OrderedDict()
for r in sorted(rows, key=lambda r: (r['family'], r['rtl_master'], r['item'])):
    kits.setdefault(r['reference'], dict(family=r['family'], rtl_master=r['rtl_master'], absorbs=[], replicas=0))
    kits[r['reference']]['replicas'] += r['replicas']
    if r['reference'] != r['item']:
        kits[r['reference']]['absorbs'].append(r['item'])
with open(OUT.replace('map.tsv', 'kits.tsv'), 'w') as f:
    f.write('kit_item\tfamily\trtl_master\tstate\treplicas_after_collapse\tabsorbs_on_collapse\n')
    for k, v in kits.items():
        f.write(f"{k}\t{v['family']}\t{v['rtl_master']}\t{owners.get(k, '?')}\t{v['replicas']}\t{','.join(v['absorbs']) or '-'}\n")
print(len(kits), 'kit references;', len({r['rtl_master'] for r in rows}), 'RTL masters')
