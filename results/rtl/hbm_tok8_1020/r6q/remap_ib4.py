#!/usr/bin/env python3
"""HBM-TOK8: R6 fixture config -> die pslice_c5 bank numbering. The die's leaf (ot_hbm_su_programme_pgcol EDGES 7111)
has IB = 4 index banks (local 0..3) and the dictionary from local bank 4; the R6 generator lowered each column with the
standalone EDGES = N = 672 image (IB = 1, dictionary from local 1). Main's su_programme_compile.lower_columns
(resident_edges=7111, used by layer_images / qwen_layer_images) applies exactly this shift.
    remap_ib4.py IN/config.mem OUT/config_ib4.mem"""
import sys
out = []
for l in open(sys.argv[1]):
    if not l.strip():
        continue
    c = int(l, 16); bank = c >> 264; col, loc = bank >> 5, bank & 31
    if loc >= 1:
        loc += 3
    out.append(format((c & ((1 << 264) - 1)) | (((col << 5) | loc) << 264), "070x"))
open(sys.argv[2], "w").write("\n".join(out) + "\n")
