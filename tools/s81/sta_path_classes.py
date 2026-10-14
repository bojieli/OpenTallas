#!/usr/bin/env python3
"""Group the failing endpoints of an S81 die STA `-format end` report by path class.
usage: sta_classes.py <plan.json.gz> <end_<corner>.rpt> <kit clock_delivery.json> <out.json>
class key = (clock group kind, hop class, launch master.port -> capture master.port); the launch end comes from the
plan's hop list (the die netlist has one driver per inter-tile bit)."""
import sys, json, gzip, re
from collections import defaultdict

plan, rpt, cdj, out = sys.argv[1:5]
p = json.load(gzip.open(plan))
mst = {i[0]: i[1] for i in p['insts']}
drv = {}
for h in p['hops']:
    bus, cls, bits, si, sp, di, dp = h[:7]
    L = h[-1] if isinstance(h[-1], (int, float)) else None
    drv.setdefault((di, dp.split('[')[0]), []).append((si, sp.split('[')[0], cls, L, bus))
cd = json.load(open(cdj))['tiles']
view = lambda m: cd.get(m, {}).get('view', '?')
norm = lambda m: re.sub(r'__.*$', '', re.sub(r'(dsfd_h?stn[hv])_\d+(x\d+)?', r'\1_N', re.sub(r'(dsfd_rly)_\d+_', r'\1_N_', m)))
agg = defaultdict(lambda: dict(n=0, viol=0, wns=1e9, tns=0.0, Lmax=0.0, Lsum=0.0, Ln=0, ex=None, groups=set(), masters=set()))
grp = None
tot = dict(n=0, viol=0)
line_re = re.compile(r'^(\S+?)/([^/\s\[]+)(\[\d+\])?\s+\((\S+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)')
for ln in open(rpt, errors='ignore'):
    if ln.startswith(('min_delay', 'max_delay')):
        grp = ln.split()[-1]
        continue
    m = line_re.match(ln)
    if not m:
        continue
    inst, port, _, em, req, act, sl = m.groups()
    sl = float(sl)
    tot['n'] += 1
    ds = drv.get((inst, port))
    if ds:
        si, sp, cls, L, bus = ds[0]
        sm = mst.get(si, '?')
    else:
        si, sp, cls, L, sm = None, '?', 'no_plan_hop', None, '?'
    gk = 'col' if grp.startswith('ck_col_') else grp
    key = (gk, cls, f'{norm(sm)}.{sp}', f'{norm(em)}.{port}', f'{view(sm)}->{view(em)}')
    a = agg[key]
    a['n'] += 1
    a['masters'].add((sm, em))
    if L is not None:
        a['Lmax'] = max(a['Lmax'], L); a['Lsum'] += L; a['Ln'] += 1
    if sl < 0:
        tot['viol'] += 1
        a['viol'] += 1; a['tns'] += sl
    if sl < a['wns']:
        if True:
            a['wns'] = sl; a['ex'] = f'{si}/{sp} -> {inst}/{port} req {req} act {act} ({grp})'
rows = []
for k, a in agg.items():
    rows.append(dict(group=k[0], cls=k[1], launch=k[2], capture=k[3], views=k[4], endpoints=a['n'], violators=a['viol'],
                     wns_ps=round(a['wns'], 1), tns_ns=round(a['tns'] / 1000, 1), len_max_um=round(a['Lmax'], 1),
                     len_mean_um=round(a['Lsum'] / a['Ln'], 1) if a['Ln'] else None, example=a['ex'],
                     master_pairs=len(a['masters'])))
rows.sort(key=lambda r: r['wns_ps'])
json.dump(dict(report=rpt, endpoints=tot['n'], violators=tot['viol'], classes=rows), open(out, 'w'), indent=1)
print(rpt, tot)
for r in rows:
    if r['violators'] or '--all' in sys.argv: print('%-10s %-12s %-34s -> %-34s %-18s n %7d viol %7d wns %8.1f tns %9.1f ns L %6.1f/%s' % (
        r['group'], r['cls'], r['launch'], r['capture'], r['views'], r['endpoints'], r['violators'], r['wns_ps'], r['tns_ns'],
        r['len_max_um'], r['len_mean_um']))
