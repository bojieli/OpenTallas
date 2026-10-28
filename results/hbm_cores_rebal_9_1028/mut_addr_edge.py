#!/usr/bin/env python3
"""HBM-CORES-REBAL-9: first live serial edge of the ADDR-mutant field (quarter 1 control[540+:24]) in a compiled
vector (vec/serial/expected.mem).  MLAT4/WCOPY0 -> 1040 (the TB default); m5w1 -> 1041.  Prints the edge."""
import sys
from pathlib import Path
QW = 2422
L = [x for x in Path(sys.argv[1]).read_text().split() if x and not x.startswith(("@", "//"))]
print(next(e for e, h in enumerate(L) if (int(h, 16) >> (QW + 680 + 540)) & 0xFFFFFF))
