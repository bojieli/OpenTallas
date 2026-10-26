import sys, os
o, gt = sys.argv[1], sys.argv[2]
r0 = [int(l.split()[1]) for l in open(os.path.join(o, "gold/tiles_gold.txt")) if l.split()[0] == gt][0]
lg = [int(x, 16) for x in open(os.path.join(o, "gold/lg", gt + ".hex")).read().split()]
import struct
f = [struct.unpack(">f", struct.pack(">I", x))[0] for x in lg]
best = max(range(128), key=lambda k: (f[k], -k)); sec = max((k for k in range(128) if k != best), key=lambda k: (f[k], -k))
out = []
for ln in open(os.path.join(o, "rec.hex")).read().split():
    v = int(ln, 16)
    if v >> 66 == r0:
        v = (v & ~(((1 << 49) - 1) << 1)) | ((r0 + sec) << 33) | (lg[sec] << 1)
    out.append(f"{v:021x}")
open(os.path.join(o, "rec_mut.hex"), "w").write("\n".join(out) + "\n")
print(f"mut_rec: {gt} row0 {r0}: best {r0 + best} -> second {r0 + sec} {lg[sec]:08x}")
