#!/usr/bin/env python3
"""PG-ACTIVITY-2: map bench SM VCD toggle rates (act_SM.txt, keys g_c[i].g_p[j].g_tp.u_t.g_lf[k].u_lh.u_tcc...) onto a hard
core's register names (regs.txt, odb inst names) by LONGEST common hierarchical suffix (>= 2 segments; replicas averaged).
Writes "normname rate" with normname = core_power_meas.tcl norm() of the odb name (strip '$_...', '/'->'.', drop '\\'),
so the tcl's exact lookup hits.  usage: sm_match.py ACT.txt REGS.txt OUT.txt [PREFIX]   (PREFIX prepended to core names, e.g. u_bdc.)"""
import re, sys
from collections import defaultdict
act, regs, outp = sys.argv[1:4]; pre = sys.argv[4] if len(sys.argv) > 4 else ""
SPLIT = re.compile(r"\.(?![^\[]*\])")
def norm(n): n = re.sub(r"\$_.*$", "", n); n = n.replace("/", "."); return n.replace("\\", "")
names = [norm(l.strip()) for l in open(regs) if l.strip()]
need = {}
for n in names:
    s = SPLIT.split(pre + n)
    for j in range(0, len(s) - 1): need.setdefault(".".join(s[j:]), None)
acc = defaultdict(lambda: [0.0, 0])
for l in open(act):
    k, r = l.rsplit(" ", 1); r = float(r); s = SPLIT.split(k)
    for j in range(len(s) - 1):
        suf = ".".join(s[j:])
        if suf in need: a = acc[suf]; a[0] += r; a[1] += 1; break   # longest suffix of this VCD key that a core name needs
out = open(outp, "w"); hit = 0; seg = defaultdict(int)
for n in names:
    s = SPLIT.split(pre + n)
    for j in range(len(s) - 1):
        suf = ".".join(s[j:])
        if suf in acc:
            a = acc[suf]; out.write(f"{n} {a[0] / a[1]}\n"); hit += 1; seg[len(s) - j] += 1; break
print("regs", len(names), "matched", hit, "frac %.3f" % (hit / max(len(names), 1)), "suffix-len hist", dict(sorted(seg.items())))
