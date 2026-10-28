import re, sys
t = open(sys.argv[1]).read()
drv = {}
for m in re.finditer(r'(dsfd_rly_1_\w+) (\w+) \(\.ck\(([\w\[\]]+)\), \.rs\((\w+)\), \.i\((\w+)\), \.o\((\w+)\)\);', t):
    drv[m[6]] = m[5]
def depth(n):
    d = 0
    while n in drv: n = drv[n]; d += 1
    return d, n
for f in sys.argv[2].split(','):
    ena = re.search(rf'fwd_r_f_{f} \(\.CLK\((\w+)\), \.ENA\((\w+)\)', t)
    ld = re.search(rf'ld_r_f_{f} \(.*?\.rs\((\w+)\)', t)
    de, re_ = depth(ena[2]); dl, rl = depth(ld[1])
    print(f, 'gate ENA depth', de, 'landing rs depth', dl, 'diff(land-gate)', dl - de, 'roots', re_, rl)
