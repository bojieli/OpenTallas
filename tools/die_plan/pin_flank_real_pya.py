# klayout -b -r pin_flank_real_pya.py -rd gds=CORE.gds -rd lef=VIEW.lef -rd gds_layer=30 -rd layer=M3 -rd out=REAL.json
# C-VIEW-OBS-PIN-ABUT: real metal of the signed core GDS inside the thin OBS strips of a view (the only OBS that pin_flank_clear.py may open); exported once per view family.
import hashlib
import json
import re
import pya

ly = pya.Layout()
ly.read(gds)
top = [ly.cell(i) for i in ly.each_top_cell()][0]
li = ly.layer(int(gds_layer), 0)
real = pya.Region(top.begin_shapes_rec(li))
real.merge()
strips = pya.Region()
io, lay = False, None
for ln in open(lef).read().splitlines():
    s = ln.strip()
    if s == "OBS":
        io = True
        continue
    m = re.match(r"LAYER\s+(\w+)", s)
    if m:
        lay = m.group(1)
    m = re.match(r"RECT\s+(?:MASK\s+\d+\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", s)
    if io and m and lay == layer:
        r = [float(v) for v in m.groups()]
        if min(r[2] - r[0], r[3] - r[1]) <= 0.05 and max(r[2] - r[0], r[3] - r[1]) < 0.5:
            strips.insert(pya.Box(round(r[0] / ly.dbu), round(r[1] / ly.dbu), round(r[2] / ly.dbu), round(r[3] / ly.dbu)))
strips.merge()
inter = (strips & real)
rects = [[round(p.bbox().left * ly.dbu, 4), round(p.bbox().bottom * ly.dbu, 4), round(p.bbox().right * ly.dbu, 4), round(p.bbox().top * ly.dbu, 4)] for p in inter.each()]
json.dump(dict(schema="opentallas.pin_flank_real.v1", layer=layer, gds=gds.split("/")[-1], gds_sha256=hashlib.sha256(open(gds, "rb").read()).hexdigest(),
               lef_sha256=hashlib.sha256(open(lef, "rb").read()).hexdigest(), strips_um2=strips.area() * ly.dbu * ly.dbu, real_in_strips_um2=inter.area() * ly.dbu * ly.dbu,
               real_um={layer: rects}), open(out, "w"), indent=0)
print("REAL", layer, len(rects), "rects", inter.area() * ly.dbu * ly.dbu)
