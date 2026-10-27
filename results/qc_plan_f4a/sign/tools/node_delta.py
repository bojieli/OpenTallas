import sys
def ld(fn):
    d = {}
    for l in open(fn):
        f = l.rstrip('\n').split('\t'); d[f[0]] = (f[1], float(f[2]), float(f[3]), float(f[4]), f[5])
    return d
g, r = ld(sys.argv[1]), ld(sys.argv[2]); pat = sys.argv[3]
for k in sorted(g, key=lambda k: g[k][3]):
    if pat in k: print('%-22s %-20s (%6.1f,%6.1f) grt %6.1f rcx %6.1f d %+5.1f  in %s' % (k, g[k][0], g[k][1], g[k][2], g[k][3], r[k][3], r[k][3]-g[k][3], g[k][4]))
