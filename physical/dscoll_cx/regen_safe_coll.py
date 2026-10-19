#!/usr/bin/env python3
"""Regenerate safe collective kits, including the pre-tapcell cell-band hook."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for side in ("w","e"):
    kit=root/f"physical/ref_tile/dscoll_lane_{side}_ltr"
    subprocess.run(["python3",str(root/"tools/ref_tile/ref_tile.py"),"gen",str(kit/"spec.json")],cwd=root,check=True)
    with (kit/"place.tcl").open("a") as out:
        out.write("\nsource /src/physical/dscoll_cx/coll_cell_band.tcl\n")
