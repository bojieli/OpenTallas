# QC-CORES-2 F4I gate: every keep-out band x-range from pa_bands_f4i.json has blockages in the DB, and no movable cell overlaps
# a blockage.  Info: movable cells still inside a band x-range (only possible in the y-cuts left for fixed plan cells).
import os, odb, json
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
bands = [(round(s0 * u), round(s1 * u)) for s0, s1 in json.load(open(os.environ["BANDS"]))["bands_um"]]
blk = [k.getBBox() for k in b.getBlockages()]
xs = set((k.xMin(), k.xMax()) for k in blk)
have = sum(1 for bd in bands if bd in xs)
ov = []; inband = 0
for i in b.getInsts():
    m = i.getMaster()
    if m.isBlock() or i.getPlacementStatus() in ("FIRM", "LOCKED", "COVER"): continue
    bb = i.getBBox()
    if any(bb.xMax() > s0 and bb.xMin() < s1 for s0, s1 in bands): inband += 1
    for k in blk:
        if bb.xMax() > k.xMin() and bb.xMin() < k.xMax() and bb.yMax() > k.yMin() and bb.yMin() < k.yMax():
            ov.append((i.getName(), m.getName(), bb.xMin() / u, bb.yMin() / u)); break
ok = have == len(bands) and not ov
print("F4I_PA_CHECK %s bands %d in_db %d blockages %d movable_overlap %d movable_in_band_cuts %d first %s"
      % ("PASS" if ok else "FAIL", len(bands), have, len(blk), len(ov), inband, ov[:5]))
