#!/usr/bin/env python3
"""TOK-QW-5: write a reduced copy of qwen_compute_bound_top keeping only instances whose type matches KEEP regex
(and keeping at most N of them, every k-th), for frontend memory bisection. Wires/ports untouched."""
import re, sys
src, dst, keep_re, nmax = sys.argv[1], sys.argv[2], re.compile(sys.argv[3]), int(sys.argv[4])
hdr = re.compile(r'^    ([A-Za-z0-9_]+) (#\(.*\) )?([A-Za-z0-9_]+) \($')
out, skip, kept, dropped = [], False, 0, 0
for line in open(src):
    m = hdr.match(line)
    if m:
        ok = bool(keep_re.search(m.group(1))) and kept < nmax
        skip = not ok
        kept += ok; dropped += (not ok)
    if not skip:
        out.append(line)
    if skip and line.startswith('    );'):
        skip = False
open(dst, 'w').writelines(out)
print(f"kept {kept} dropped {dropped}")
