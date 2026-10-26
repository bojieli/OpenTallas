"""Write explicit macro placement with a legal south register band.

Run with OpenROAD Python: INPUT_ODB, OUTPUT_TCL, SOUTH_BAND_UM (default 12),
MACRO_HALO_UM (default 4.32). Connected vertical macro banks move together;
interfaces, outlines and cycle counts remain unchanged. Collisions fail closed.
The emitted placement still requires render/review and a fresh floorplan build.
"""
import math
import os
from pathlib import Path
import openroad as ord

tech = ord.Tech()
design = ord.Design(tech)
design.readDb(os.environ["INPUT_ODB"])
block = design.getBlock()
dbu = tech.getDB().getTech().getDbUnitsPerMicron()
halo = float(os.environ.get("MACRO_HALO_UM", "4.32"))*dbu
band = float(os.environ.get("SOUTH_BAND_UM", "12"))*dbu
core = block.getCoreArea()
macros = [i for i in block.getInsts() if i.getMaster().isBlock()]
boxes = [i.getBBox() for i in macros]
groups = [{i} for i in range(len(macros))]
for i, a in enumerate(boxes):
    for j, b in enumerate(boxes[:i]):
        gap = max(a.yMin(), b.yMin())-min(a.yMax(), b.yMax())
        if min(a.xMax(), b.xMax()) > max(a.xMin(), b.xMin()) and gap <= 2*halo:
            left = next(g for g in groups if i in g)
            right = next(g for g in groups if j in g)
            if left is not right:
                left.update(right)
                groups.remove(right)
pitch = block.getRows()[0].getSite().getHeight()
delta = {}
for group in groups:
    bottom = min(boxes[i].yMin() for i in group)
    dy = max(0, math.ceil((core.yMin()+halo+band-bottom)/pitch)*pitch)
    for i in group:
        delta[i] = dy
new = [(b.xMin(), b.yMin()+delta[i], b.xMax(), b.yMax()+delta[i]) for i,b in enumerate(boxes)]
for i, a in enumerate(new):
    if a[1] < core.yMin() or a[3] > core.yMax():
        raise RuntimeError(f"macro bank exceeds core: {macros[i].getName()}")
    for j, b in enumerate(new[:i]):
        if delta[i] != delta[j] and a[0] < b[2]+2*halo and a[2]+2*halo > b[0] and a[1] < b[3]+2*halo and a[3]+2*halo > b[1]:
            raise RuntimeError(f"macro bank halo collision: {macros[i].getName()} / {macros[j].getName()}")
lines=[]
for i, inst in enumerate(macros):
    a=new[i]
    lines.append(f"place_macro -macro_name {{{inst.getName()}}} -location {{{a[0]/dbu:.6f} {a[1]/dbu:.6f}}} -orientation {inst.getOrient()}")
Path(os.environ["OUTPUT_TCL"]).write_text("\n".join(lines)+"\n")
print("SOUTH_MACRO_CORRIDOR",len(macros),"macros",sum(v>0 for v in delta.values()),"moved", "band_um",band/dbu)
