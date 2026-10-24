"""Placed partition dump (S81-P10 copy of the CORE-S81-SVC dump; all non-PG BTerms incl. clock taps): ODB=<odb> OUT=<csv> openroad -python -exit dump_placed.py
Rows: kind,name,master,x,y,w,h  (kind = std|ff|buf|macro|pin; pin rows carry the flop it lands on, if any, in master)."""
import os
import re

import odb

db = odb.dbDatabase.create()
db = odb.read_db(db, os.environ["ODB"])
blk = db.getChip().getBlock()
u = blk.getDbUnitsPerMicron()
BUF = re.compile(r"^(BUF|INV|HB)")
with open(os.environ["OUT"], "w") as fh:
    fh.write("kind,name,master,x,y,w,h\n")
    for i in blk.getInsts():
        m = i.getMaster()
        x, y = i.getLocation()
        k = "macro" if m.isBlock() else ("ff" if "DFF" in m.getName() else ("buf" if BUF.match(m.getName()) else
                                                                          ("tap" if m.getName().startswith("TAP") else "std")))
        fh.write(f"{k},{i.getName()},{m.getName()},{x / u:.3f},{y / u:.3f},{m.getWidth() / u:.3f},{m.getHeight() / u:.3f}\n")
    for bt in blk.getBTerms():
        if bt.getSigType() in ("POWER", "GROUND"):
            continue
        bb = bt.getBBox()
        n = bt.getNet()
        best = ""
        if n:
            for it in n.getITerms():
                if "DFF" in it.getInst().getMaster().getName():
                    best = it.getInst().getName()
                    break
        fh.write(f"pin,{bt.getName()},{best},{(bb.xMin() + bb.xMax()) / 2 / u:.3f},{(bb.yMin() + bb.yMax()) / 2 / u:.3f},0,0\n")
