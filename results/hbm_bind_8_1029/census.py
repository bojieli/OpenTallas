"""HBM-BIND-8: census of the UNPLANNED crossings of a strict bind (what crosses: driver/sink cells, glue vs leaf).
Usage: census.py WT PLAN MANIFEST ELAB OUT_JSON [LANE_ADD_REPORT]
Re-runs Binder map_cells/analyse/build_buses (bind.py of WT, the per-bit unplanned list un-capped in a private copy of
the module text; no tool change) and writes per UNPLANNED pair: driver cells (path, module, kind, port, bits) and the
sink cells (path, module, kind, port), plus per cell the data-bit connections per partition (glue re-home input)."""
import sys, json, re, collections, types
from pathlib import Path
w, plan, man, elab, out = sys.argv[1:6]
lar = json.loads(Path(sys.argv[6]).read_text()) if len(sys.argv) > 6 else None
sys.path.insert(0, str(Path(w) / 'tools')); sys.path.insert(0, str(Path(w) / 'tools/die_plan'))
src = (Path(w) / 'tools/die_plan/bind.py').read_text()
assert src.count('len(self.unplanned_bits) < 5000') == 1
mod = types.ModuleType('bind'); mod.__file__ = str(Path(w) / 'tools/die_plan/bind.py'); sys.modules['bind'] = mod
exec(compile(src.replace('len(self.unplanned_bits) < 5000', 'True'), mod.__file__, 'exec'), mod.__dict__)
B = mod
a = json.loads(Path(man).read_text()); p = json.loads(Path(plan).read_text()); p['asbuilt'] = a
b = B.Binder(p, json.loads(Path(elab).read_text()), Path(plan).parent, a['base'])
b.map_cells(); b.analyse(); b.build_buses()
F, G, cp = b.F, b.G, b.cpart
print('unplanned pairs', len(b.unplanned), 'bits', sum(b.unplanned.values()), flush=True)
ctl = lambda pn: bool(re.fullmatch(r'(clk.*|clock.*|ck(_.*)?|rst.*|reset.*|arst.*|srst.*)', pn.lower()))
pidx = {c.path: i for i, c in enumerate(F.cells)}
# sink index: (sci, spn, sb, dst part) -> [(ci, pn)]
sk = collections.defaultdict(list)
for (ci, pn, i), d in b.sinks.items():
    if d and d[0] == 'x':
        _, sp, sci, spn, sb, st, dp = d
        sk[(sci, spn, sb, dp)].append((ci, pn))
pairs = collections.defaultdict(lambda: dict(bits=0, drivers=collections.Counter(), sinks=collections.Counter()))
cells_of_interest = set()
for u in b.unplanned_bits:
    sp, dp = u['src_part'], u['dst_part']
    m = re.fullmatch(r'(.*)\.([^.\[]+)\[(\d+)\]', u['driver'])
    dpath, spn, bit = m.group(1), m.group(2), int(m.group(3))
    sci = pidx[dpath]
    pr = pairs[(sp, dp)]; pr['bits'] += 1
    pr['drivers'][(dpath, F.cells[sci].module, G.kind[sci], spn)] += 1
    cells_of_interest.add(sci)
    for ci, pn in sk.get((sci, spn, bit, dp), []):
        pr['sinks'][(F.cells[ci].path, F.cells[ci].module, G.kind[ci], pn)] += 1
        cells_of_interest.add(ci)
# per-cell partition connectivity (data bits, both directions) for the cells on unplanned crossings
conn = {}
drv = collections.defaultdict(list); lds = collections.defaultdict(list)
for i, c in enumerate(F.cells):
    if i not in cp: continue
    for pn, bs in c.ports.items():
        if ctl(pn): continue
        t = drv if G.dirs[i].get(pn) == 'output' else lds
        for n in bs:
            if isinstance(n, int): t[n].append(i)
for i in cells_of_interest:
    cin, cout = collections.Counter(), collections.Counter()
    for pn, bs in F.cells[i].ports.items():
        if ctl(pn): continue
        isout = G.dirs[i].get(pn) == 'output'
        for n in bs:
            if not isinstance(n, int): continue
            for o in (lds[n] if isout else drv[n]):
                if o == i or o not in cp: continue
                (cout if isout else cin)[cp[o]] += 1
    conn[F.cells[i].path] = dict(part=cp[i], kind=G.kind[i], module=F.cells[i].module, ytype=getattr(F.cells[i], 'ytype', None),
                                 inb=dict(cin), outb=dict(cout), mapkey=next((k for k in [F.cells[i].path] if k in b.R.parts), None))
far = {(r['src'], r['dst']): r for r in (lar or {}).get('far', [])}
fail = {(r['src'], r['dst']): r for r in (lar or {}).get('failed', [])}
res = []
for (sp, dp), pr in sorted(pairs.items(), key=lambda kv: -kv[1]['bits']):
    res.append(dict(src=sp, dst=dp, bits=pr['bits'], unplanned=b.unplanned[(sp, dp)],
                    cls='far' if (sp, dp) in far else 'failed' if (sp, dp) in fail else 'other',
                    gap_um=far.get((sp, dp), {}).get('gap_um'),
                    drivers=[dict(path=k[0], module=k[1], kind=k[2], port=k[3], bits=v) for k, v in pr['drivers'].most_common()],
                    sinks=[dict(path=k[0], module=k[1], kind=k[2], port=k[3], bits=v) for k, v in pr['sinks'].most_common()]))
Path(out).write_text(json.dumps(dict(schema='hbm_bind_8.census.v1', plan=plan, manifest=man,
                                     n_pairs=len(b.unplanned), n_bits=sum(b.unplanned.values()),
                                     pairs=res, cells=conn, roots=b.root), indent=0))
for r in res:
    print(r['cls'], r['src'], '->', r['dst'], r['bits'], r['gap_um'])
    for d in r['drivers'][:4]: print('   D', d)
    for d in r['sinks'][:4]: print('   S', d)
