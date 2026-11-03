import re, sys
from collections import Counter
def load(p):
    out = []
    for l in open(p):
        if 'attribute \\src' in l: continue
        out.append(re.sub(r'\$[0-9]+', '$N', l.rstrip()))
    return Counter(out)
a, b = load(sys.argv[1]), load(sys.argv[2])
d1, d2 = a - b, b - a
print("only_base", sum(d1.values()), "only_new", sum(d2.values()))
for k, v in list(d1.items())[:25]: print("<", v, k)
for k, v in list(d2.items())[:40]: print(">", v, k)
