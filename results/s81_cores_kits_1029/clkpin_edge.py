#!/usr/bin/env python3
"""S81-CORES-KITS 10-29 (ASK default, edge form): child contract LEF with ONLY PIN clk replaced by one M5 0.048x0.48 rect
on the S edge (GEOM-21 size/layer), x on the M5 track (0.012 + 0.048 k). Everything else byte-identical.
usage: clkpin_edge.py LEF X_CENTRE"""
import re
import sys
from pathlib import Path

lef, xc = sys.argv[1], float(sys.argv[2])
t = Path(lef).read_text()
k = (xc - 0.012) / 0.048
assert abs(k - round(k)) < 1e-6, "x not on the M5 track"
blk = re.search(r"  PIN clk\n.*?  END clk\n", t, re.S)
assert blk and t.count("  PIN clk\n") == 1
new = ("  PIN clk\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n"
       f"        RECT  {xc-0.024:.3f} 0 {xc+0.024:.3f} 0.48 ;\n    END\n  END clk\n")
Path(lef).write_text(t[:blk.start()] + new + t[blk.end():])
print(lef, "clk S-edge M5 centre", xc)
