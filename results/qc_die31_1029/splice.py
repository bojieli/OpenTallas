import re, sys
orig, eco, out, nets = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
O = open(orig).read(); E = open(eco).read()
def block(t, n):
    m = re.search(r"\n    - %s \(.*?;\n" % re.escape(n), t, re.S)
    return m
for n in nets:
    mo, me = block(O, n), block(E, n)
    assert mo and me and "ROUTED" in me.group(0), n
    O = O[:mo.start()] + me.group(0) + O[mo.end():]
open(out, "w").write(O); print("SPLICED", nets)
