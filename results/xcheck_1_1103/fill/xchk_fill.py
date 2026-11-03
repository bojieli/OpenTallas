"""XCHECK-1 owner question 11-03: per type slot area, fill = cell area / (slot - macros), wasted = slot - (cell/0.40 + macros).
usage: python3 -I xchk_fill.py WT DIE PLAN.json GEOM.tsv [--evidence F ...] > out.json
cell area: latest kit auto_geom (fill_of_free x free area) when the type has one, else cells.py estimate x the die's
median measured um2/cell (kit samples; ASAP7 fallback 0.12 um2).  Macros: memory-macro LEF SIZE of contents modules
(ot_rom_* / sram / phy) plus hard-core slots (occupied: each core has its own GEOM); cells.py estimates may include core cells (upper bound on glue fill)."""
import glob, json, os, re, statistics, sys
from collections import Counter, defaultdict
wt, die, plan = sys.argv[1:4]; geomf = sys.argv[4]
ev = sys.argv[sys.argv.index('--evidence') + 1:] if '--evidence' in sys.argv else []
sys.path.insert(0, os.path.join(wt, 'tools/die_plan'))
import cells as C
raw = json.load(open(plan)); T = raw['partition_types']
n_inst = Counter(p['type'] for p in raw['partitions'])
est, _src = C.estimate(raw, plan_dir=os.path.dirname(plan) or '.', evidence=ev)
# macro areas from LEFs
mac = {}
for lef in glob.glob(os.path.join(wt, 'physical', '*', '*', '*.lef')):
    m = os.path.splitext(os.path.basename(lef))[0]
    if m in mac: continue
    try:
        s = open(lef, errors='ignore').read(20000)
        g = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', s)
        if g: mac[m] = float(g.group(1)) * float(g.group(2))
    except OSError:
        pass
# geom: latest per type for this die
G = {}
for ln in open(geomf):
    f = ln.rstrip('\n').split('\t')
    if len(f) < 10 or f[0] != die: continue
    ty = f[2].split('__cl')[0] if f[2] not in T else f[2]
    try:
        r = dict(mt=int(f[3]), w=float(f[4]), h=float(f[5]), fill=float(f[6]), mp=float(f[7]), sc=int(f[8]))
    except ValueError:
        continue
    for k in (f[2], ty):
        if k in T and (k not in G or G[k]['mt'] < r['mt']): G[k] = r
um2 = [ (g['fill'] * g['w'] * g['h'] * (1 - g['mp'] / 100)) / g['sc'] for g in G.values() if g['sc'] > 1000 and g['fill'] > 0]
avg = statistics.median(um2) if um2 else 0.12
rows = []
for tn, n in n_inst.items():
    t = T[tn]; w, h = t['outline_um']; slot = w * h
    macro = sum(mac.get(c.get('module', ''), 0) for c in t.get('contents', []) if isinstance(c, dict)
                if not t.get('hard') or True)
    core = sum(c['outline_um'][0] * c['outline_um'][1] for c in t.get('hard_cores') or [])
    macro += core
    src = 'none'
    if t.get('hard') and not t.get('hard_cores'):
        cell, macro, src = 0.0, slot, 'hard-IP'
    elif tn in G:
        g = G[tn]; cell = g['fill'] * g['w'] * g['h'] * (1 - g['mp'] / 100); macro = g['mp'] / 100 * g['w'] * g['h']; src = 'kit'
    elif tn in est:
        cell = est[tn][0] * avg; src = 'est'
    else:
        cell = None
    if cell is None:
        rows.append(dict(type=tn, n=n, slot=slot, macro=macro, core=core, cell=None, fill=None, waste=None, src=src)); continue
    macro = min(macro, slot)
    free = max(slot - macro, 1e-9)
    fill = cell / free
    waste = max(0.0, slot - (cell / 0.40 + macro)) if src != 'hard-IP' else 0.0
    rows.append(dict(type=tn, n=n, slot=slot, macro=macro, core=core, cell=cell, fill=fill, waste=waste, src=src))
A = raw['die']['outline_um'][0] * raw['die']['outline_um'][1]
tot = lambda k, f=lambda r: True: sum(r[k] * r['n'] for r in rows if r[k] is not None and f(r))
out = dict(die=die, die_mm2=A / 1e6, um2_per_cell=avg, n_types=len(rows),
           slot_mm2=tot('slot') / 1e6, macro_mm2=tot('macro') / 1e6, core_mm2=tot('core') / 1e6, cell_mm2=tot('cell') / 1e6,
           covered_kit=sum(1 for r in rows if r['src'] == 'kit'), covered_est=sum(1 for r in rows if r['src'] == 'est'),
           hardip=sum(1 for r in rows if r['src'] == 'hard-IP'), unknown=[r['type'] for r in rows if r['cell'] is None],
           slot_lt015_mm2=tot('slot', lambda r: r['fill'] is not None and r['src'] != 'hard-IP' and r['fill'] < 0.15) / 1e6,
           recoverable_mm2=tot('waste') / 1e6,
           top=sorted(([r['type'], r['n'], round(r['slot'] / 1e6, 3), round(r['fill'], 3), round(r['waste'] * r['n'] / 1e6, 2),
                        round(r['macro'] / max(r['slot'], 1), 2), r['src']] for r in rows if r['waste']),
                      key=lambda x: -x[4])[:12])
print(json.dumps(out))
