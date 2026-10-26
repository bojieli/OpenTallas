# compare clock-net (ck_*) global-route guides of two runs: identical routes => clock RC/skew results carry over
import sys, hashlib
def load(f):
    d = {}; net = None; buf = []
    for l in open(f):
        l = l.strip()
        if net is None: net = l; continue
        if l == "(": buf = []; continue
        if l == ")":
            if net.startswith(("ck_", "t_")) or net == "root": d[net] = sorted(buf)
            net = None; continue
        buf.append(l)
    return d
a, b = load(sys.argv[1]), load(sys.argv[2])
same = sum(1 for n in a if n in b and a[n] == b[n]); diff = [n for n in a if n in b and a[n] != b[n]]
print("clock nets", len(a), len(b), "identical", same, "differ", len(diff), "only_a", len(set(a) - set(b)), "only_b", len(set(b) - set(a)))
print("differ sample", diff[:5])
