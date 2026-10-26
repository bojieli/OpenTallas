#!/usr/bin/env python3
"""TOKd-HBM2 diagnostic replays from a built slice replay dir (hdr/val/msk.mem, same binary):
  shift : rec R stream events at cyc >= FROM moved +D edges (far-end drives, ring/VM/fault checks); truncated at MAXC
  probe : rec R ring_out checks replaced by val 0 / full-mask checks on the 4 SW ring outputs every edge [A,B] -> SHOWVAL
          prints the die's actual flit on every nonzero edge."""
import sys, os, shutil
mode, src, dst = sys.argv[1:4]
R, FROM, D, MAXC = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
H = [l.strip() for l in open(f"{src}/hdr.mem")]
V = [l.strip() for l in open(f"{src}/val.mem")]
M = [l.strip() for l in open(f"{src}/msk.mem")]
RING = (58, 59, 84, 85)
ev = []
for h, v, m in zip(H, V, M):
    x = int(h, 16); k = x >> 62
    if k not in (1, 2): continue
    dom = (x >> 60) & 3; port = (x >> 44) & 0xffff; rec = ((x >> 32) & 0xfff) - 1; cyc = x & 0xffffffff
    if dom == 0 and rec == R and cyc >= FROM:
        if mode == "shift": cyc += D
        elif mode == "probe" and k == 2 and port in RING: continue
    if cyc > MAXC: continue
    ev.append([k, dom, port, rec, cyc, v, m])
if mode == "probe":
    full = "f" * len(M[0])
    for c in range(FROM, D + 1):
        for p in RING:
            ev.append([2, 0, p, R, c, "0", full])
ev.sort(key=lambda e: (e[1], e[4]))
os.makedirs(dst, exist_ok=True)
with open(f"{dst}/hdr.mem", "w") as fh, open(f"{dst}/val.mem", "w") as fv, open(f"{dst}/msk.mem", "w") as fm:
    for k, dom, port, rec, cyc, v, m in ev:
        fh.write(f"{(k << 62) | (dom << 60) | (port << 44) | ((rec + 1) << 32) | cyc:016x}\n"); fv.write(v + "\n"); fm.write(m + "\n")
    fh.write(f"{3 << 62:016x}\n"); fv.write("0\n"); fm.write("0\n")
shutil.copy(f"{src}/vm_pre.txt", f"{dst}/vm_pre.txt")
print(mode, len(ev), "events ->", dst)
