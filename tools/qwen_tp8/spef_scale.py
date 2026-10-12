#!/usr/bin/env python3
"""Scale every capacitance of a SPEF (GRT parasitics -> routed-cap sensitivity, results/physical/die_region_drt_1012:
routed RCX vs GRT net cap median +40 %, p95 +144 %).  usage: spef_scale.py IN.spef OUT.spef FACTOR"""
import sys
src, dst, f = sys.argv[1], sys.argv[2], float(sys.argv[3])
sec = None
with open(src) as fi, open(dst, 'w') as fo:
    for line in fi:
        t = line.split()
        if t and t[0].startswith('*'):
            sec = t[0]
            if t[0] == '*D_NET' and len(t) >= 3:
                t[2] = '%.6g' % (float(t[2]) * f)
                line = ' '.join(t) + '\n'
        elif sec == '*CAP' and len(t) in (3, 4):
            t[-1] = '%.6g' % (float(t[-1]) * f)
            line = ' '.join(t) + '\n'
        fo.write(line)
