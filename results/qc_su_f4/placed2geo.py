#!/usr/bin/env python3
"""QC-SU-F4: MIF0 placed core (placed.csv from dump_placed.py on 3_place.odb) -> plan .geo (same format as
master_plan_r4 su_refloor/*.geo): DIE/CORE from config.mk, clock entry + rst pin copied from the reference geo, macros
from the placement (CK = macro clk pin from the LEF), one SINK per flip-flop at its cell centre (model convention:
SRAM clk pins are not SINK rows, as in every R4/R5 geo).
usage: placed2geo.py placed.csv config.mk ref.geo LEFDIR out.geo"""
import csv
import re
import sys
from pathlib import Path

pc, cfg, ref, lefdir, out = sys.argv[1:6]
txt = Path(cfg).read_text()
die = re.search(r"DIE_AREA = ([\d. ]+)", txt).group(1).split()
core = re.search(r"CORE_AREA = ([\d. ]+)", txt).group(1).split()
pins = [l for l in open(ref) if l.startswith("PIN ")]


def lef_ck(master):
    t = (Path(lefdir) / master / f"{master}.lef").read_text()
    r = t.split("PIN clk\n", 1)[1].split(" RECT ", 1)[1].split(";")[0].split()
    return (float(r[0]) + float(r[2])) / 2, (float(r[1]) + float(r[3])) / 2


rows = list(csv.DictReader(open(pc)))
with open(out, "w") as fh:
    fh.write("DIE %.3f %.3f %.3f %.3f\n" % tuple(map(float, die)))
    fh.write("CORE %.3f %.3f %.3f %.3f\n" % tuple(map(float, core)))
    fh.writelines(pins)
    for r in rows:
        if r["kind"] == "macro":
            x, y, w, h = (float(r[k]) for k in "xywh")
            cx, cy = lef_ck(r["master"])
            fh.write("MACRO %s %s %.3f %.3f %.3f %.3f CK %.3f %.3f\n" % (r["name"], r["master"], x, y, x + w, y + h, x + cx, y + cy))
    fh.write("ISLCOUNT 0\n")
    n = 0
    for r in rows:
        if r["kind"] == "ff":
            x, y, w, h = (float(r[k]) for k in "xywh")
            fh.write("SINK %.3f %.3f %s %s CLK\n" % (x + w / 2, y + h / 2, r["master"], r["name"]))
            n += 1
print(out, "sinks", n)
