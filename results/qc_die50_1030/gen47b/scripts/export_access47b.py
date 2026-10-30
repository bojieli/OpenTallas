#!/usr/bin/env python3
"""DIE-QC-50/gen47b: read-only export of the imported provider ODB for the provider clock leaf/access tools.
geometry.json  = Codex export_geometry119.py schema (signal_shapes / obstructions / existing_supplies / die_dbu), all
                 insts (clock CKINV A/Y, partition + provider pins and OBS), block OBS, PG swires (none yet)
via_facts.json = {dbu, tech_vias_dbu} (pg_census.py recipe)
graph_actual.json = ODB clock connectivity with actual names (ck_* nets, actual inst names) for plan_provider_clock_access
graph_raw.json    = same connectivity on raw tree names (ck_ stripped) for provider_clock_loads (NOT the fixed-tree graph)
usage: openroad -python export_access47b.py ODB OUTDIR"""
import json, sys
from pathlib import Path
import odb
src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
d = odb.dbDatabase.create(); odb.read_db(d, src); b = d.getChip().getBlock(); dbu = b.getDbUnitsPerMicron()
def tr(i, s):
    sx, sy = {'R0': (1, 1), 'MX': (1, -1), 'MY': (-1, 1), 'R180': (-1, -1)}[str(i.getOrient())]
    x, y = i.getOrigin(); xx = sorted([x + sx * s.xMin(), x + sx * s.xMax()]); yy = sorted([y + sy * s.yMin(), y + sy * s.yMax()])
    return [xx[0], yy[0], xx[1], yy[1]]
obs = []; sup = []; sig = []
for i in b.getInsts():
    m = i.getMaster()
    for sh in m.getObstructions():
        ly = sh.getTechLayer()
        if ly and 1 <= ly.getRoutingLevel() <= 9: obs.append([i.getName(), ly.getName(), *tr(i, sh)])
    for it in i.getITerms():
        mt = it.getMTerm(); st = str(mt.getSigType())
        for mp in mt.getMPins():
            for sh in mp.getGeometry():
                ly = sh.getTechLayer()
                if not ly or not 1 <= ly.getRoutingLevel() <= 9: continue
                if st in ('POWER', 'GROUND'): sup.append(['VDD' if st == 'POWER' else 'VSS', ly.getName(), *tr(i, sh)])
                else: sig.append([i.getName(), mt.getName(), ly.getName(), *tr(i, sh)])
for oo in b.getObstructions():
    sh = oo.getBBox(); ly = sh.getTechLayer()
    if ly and 1 <= ly.getRoutingLevel() <= 9: obs.append(['BLOCK', ly.getName(), sh.xMin(), sh.yMin(), sh.xMax(), sh.yMax()])
nsw = 0
for net in b.getNets():
    if str(net.getSigType()) not in ('POWER', 'GROUND'): continue
    for sw in net.getSWires():
        for sh in sw.getWires():
            if sh.isVia(): continue
            ly = sh.getTechLayer(); nsw += 1
            if ly and 1 <= ly.getRoutingLevel() <= 9: sup.append(['VDD' if str(net.getSigType()) == 'POWER' else 'VSS', ly.getName(), sh.xMin(), sh.yMin(), sh.xMax(), sh.yMax()])
bb = b.getDieArea()
json.dump(dict(source=src, dbu=dbu, die_dbu=[bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax()], signal_shapes=sig, obstructions=obs,
               existing_supplies=sup), open(out / 'geometry.json', 'w'), separators=(',', ':'))
vias = {v.getName(): [[x.getTechLayer().getName(), x.xMin(), x.yMin(), x.xMax(), x.yMax()] for x in v.getBoxes() if x.getTechLayer()]
        for v in d.getTech().getVias() if v.getName() in {f'VIA{k}{k+1}' for k in range(1, 9)}}
json.dump(dict(dbu=dbu, tech_vias_dbu=vias), open(out / 'via_facts.json', 'w'))
ga = []; gr = []
for n in b.getNets():
    if not n.getName().startswith('ck_'): continue
    drv = [it.getInst().getName() for it in n.getITerms() if str(it.getMTerm().getIoType()) == 'OUTPUT']
    bt = [t.getName() for t in n.getBTerms()]
    if len(drv) + len(bt) != 1: raise SystemExit('clock net driver count %s %s %s' % (n.getName(), drv, bt))
    dv = drv[0] if drv else 'port:' + bt[0]
    ld = [it.getInst().getName() for it in n.getITerms() if str(it.getMTerm().getIoType()) == 'INPUT'
          and it.getInst().getMaster().getName().startswith('CKINV')]
    ga.append(dict(name=n.getName(), drv=dv, loads=ld))
    strip = lambda s: s[3:] if s.startswith('ck_') else s
    gr.append(dict(name=strip(n.getName()), drv=strip(dv), loads=[strip(x) for x in ld]))
for nm, g in (('graph_actual.json', ga), ('graph_raw.json', gr)):
    json.dump(dict(schema='gen47b_odb_clock_connectivity', note='ODB-derived, not the fixed-tree prebuild graph', nets=g, ports={}, endpoints={}),
              open(out / nm, 'w'))
print(json.dumps(dict(signal_shapes=len(sig), obstructions=len(obs), existing_supplies=len(sup), pg_swire_shapes=nsw, clock_nets=len(ga), vias=sorted(vias))))
