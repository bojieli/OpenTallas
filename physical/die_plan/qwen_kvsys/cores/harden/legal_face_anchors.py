"""Pack existing dedicated face flops on legal sites before detailed placement.

OpenROAD Python entry point; INPUT_ODB, OUTPUT_ODB, FACE_TABLE identify the
checkpoint and its generated ot_face_flops.txt. No cells or nets are changed.
All faces share one occupancy map, including macro keepouts. Unlike the generic
face hook, this cannot stack orthogonal face banks in the same corner.
"""
import bisect
import json
import os
from pathlib import Path

import openroad as ord

tech = ord.Tech()
design = ord.Design(tech)
design.readDb(os.environ["INPUT_ODB"])
block = design.getBlock()
dbu = tech.getDB().getTech().getDbUnitsPerMicron()
instances = {i.getName(): i for i in block.getInsts()}
faces = []
for line in Path(os.environ["FACE_TABLE"]).read_text().splitlines():
    fields = line.split("\t")
    if len(fields) >= 5 and fields[0] in instances:
        faces.append((instances[fields[0]], fields[4]))
face_names = {i.getName() for i, _ in faces}
rows = []
for row in block.getRows():
    box = row.getBBox()
    site = row.getSite()
    rows.append(dict(x0=box.xMin(), x1=box.xMax(), y=box.yMin(),
                     h=site.getHeight(), pitch=site.getWidth(),
                     orient=row.getOrient(), busy=[]))
rows.sort(key=lambda r: (r["y"], r["x0"]))

def reserve(box, padding=0):
    for row in rows:
        if row["y"] < box.yMax() and row["y"] + row["h"] > box.yMin():
            lo, hi = box.xMin() - padding, box.xMax() + padding
            if lo < row["x1"] and hi > row["x0"]:
                row["busy"].append((lo, hi))

obstacles = []
for inst in block.getInsts():
    if inst.getName() in face_names:
        inst.setPlacementStatus("PLACED")
    elif inst.getMaster().isBlock() or inst.getPlacementStatus() in ("FIRM", "LOCKED"):
        reserve(inst.getBBox(), max(r["pitch"] for r in rows))
        obstacles.append(inst.getName())
for row in rows:
    row["busy"].sort()

def intervals(row):
    left = row["x0"]
    for lo, hi in row["busy"]:
        if lo > left:
            yield left, min(lo, row["x1"])
        left = max(left, hi)
    if left < row["x1"]:
        yield left, row["x1"]

distances = []
port_distances = []
for inst, port in sorted(faces, key=lambda p: p[1]):
    bt = block.findBTerm(port)
    if bt is None:
        raise RuntimeError(f"missing face port {port}")
    box = bt.getBBox()
    px, py = (box.xMin()+box.xMax())//2, (box.yMin()+box.yMax())//2
    width, height = inst.getMaster().getWidth(), inst.getMaster().getHeight()
    best = None
    for index, row in enumerate(rows):
        if height != row["h"]:
            continue
        dy = abs(row["y"] + height//2 - py)
        if best and dy > best[0]:
            continue
        pitch = row["pitch"]
        for lo, hi in intervals(row):
            lo = row["x0"] + ((lo-row["x0"]+pitch-1)//pitch)*pitch
            hi = row["x0"] + ((hi-width-row["x0"])//pitch)*pitch
            if lo > hi:
                continue
            ideal = row["x0"] + round((px-width/2-row["x0"])/pitch)*pitch
            x = min(hi, max(lo, ideal))
            candidate = (abs(x+width//2-px)+dy, index, x)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        raise RuntimeError(f"no legal site for {inst.getName()} at {port}")
    distance, index, x = best
    row = rows[index]
    inst.setOrient(row["orient"])
    inst.setLocation(x, row["y"])
    inst.setPlacementStatus("FIRM")
    # Reserve padding on both sides for ORFS placement padding.
    bisect.insort(row["busy"], (x-row["pitch"]*2, x+width+row["pitch"]*2))
    distances.append(distance/dbu)
    port_distances.append((distance/dbu, port, inst.getName()))
design.writeDb(os.environ["OUTPUT_ODB"])
distances.sort()
print("LEGAL_FACE_ANCHORS", json.dumps(dict(count=len(distances),
    p90_um=distances[int(.9*(len(distances)-1))], max_um=max(distances),
    rows=len(rows), obstacles=len(obstacles),
    worst=sorted(port_distances, reverse=True)[:12])))
