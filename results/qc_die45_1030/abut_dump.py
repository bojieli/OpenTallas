# DIE-QC-45: dump partition (BLOCK master) instances + master pin geometry of the materialized QC die ODB for an
# offline physical abutment check.  usage (openroad -python): abut_dump.py ODB OUTDIR
import sys, json, os, collections
import odb
src, od = sys.argv[1:3]; os.makedirs(od, exist_ok=True)
db = odb.dbDatabase.create(); odb.read_db(db, src); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
insts = []; masters = {}; cls = collections.Counter()
for i in b.getInsts():
    m = i.getMaster(); cls[m.getType()] += 1
    if not m.getType().startswith("BLOCK"):
        continue
    bb = i.getBBox()
    insts.append(dict(name=i.getName(), master=m.getName(), orient=str(i.getOrient()), loc=[v / u for v in i.getLocation()],
                      bbox=[bb.xMin() / u, bb.yMin() / u, bb.xMax() / u, bb.yMax() / u],
                      nets_connected=sum(1 for it in i.getITerms() if it.getNet() is not None and it.getSigType() not in ("POWER", "GROUND"))))
    if m.getName() not in masters:
        pins = []
        for mt in m.getMTerms():
            if mt.getSigType() in ("POWER", "GROUND"):
                continue
            for mp in mt.getMPins():
                for r in mp.getGeometry():
                    pins.append([mt.getName(), r.getTechLayer().getName() if r.getTechLayer() else "?", r.xMin() / u, r.yMin() / u, r.xMax() / u, r.yMax() / u])
        masters[m.getName()] = dict(size=[m.getWidth() / u, m.getHeight() / u], pins=pins)
json.dump(dict(odb=src, master_types=dict(cls), insts=insts), open(od + "/insts.json", "w"))
json.dump(masters, open(od + "/masters.json", "w"))
print("insts", len(insts), "masters", len(masters), "pins", sum(len(v["pins"]) for v in masters.values()), dict(cls))
