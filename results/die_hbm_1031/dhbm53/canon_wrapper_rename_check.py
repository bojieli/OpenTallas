#!/usr/bin/env python3
"""DIE-HBM-53: canon wrapper vs member wrapper textual-structure check.
member names g_<word>_<n>_ -> g_<word>_k<i>_ (i = rank of n among the member's lane/bank indices per word);
compares sorted port decls + sorted body statements; reports residual diffs."""
import re, sys, collections
def load(p):
    t = open(p).read()
    t = re.sub(r"//[^\n]*", "", t)
    m = re.search(r"module\s+(\w+)\s*\((.*?)\);(.*)endmodule", t, re.S)
    ports = [re.sub(r"\s+", " ", x.strip()) for x in m.group(2).split(",") if x.strip()]
    body = [re.sub(r"\s+", " ", x.strip()) for x in m.group(3).split(";") if x.strip()]
    return m.group(1), ports, body, t
def idxmap(t):
    d = collections.defaultdict(set)
    for w, n in re.findall(r"\bg_([a-z]+)_(\d+)_", t):
        d[w].add(int(n))
    return {w: {n: i for i, n in enumerate(sorted(s))} for w, s in d.items()}
canon, mem = sys.argv[1], sys.argv[2:]
cn, cp, cb, ct = load(canon)
for mp in mem:
    mn, mpo, mb, mt = load(mp)
    im = idxmap(mt)
    def rn(s):
        s = re.sub(r"\bg_([a-z]+)_(\d+)_", lambda m: f"g_{m.group(1)}_k{im[m.group(1)][int(m.group(2))]}_", s)
        return s.replace(mn, cn)
    P1, P2 = collections.Counter(rn(x) for x in mpo), collections.Counter(cp)
    B1, B2 = collections.Counter(rn(x) for x in mb), collections.Counter(cb)
    print(mp.split("/")[-1], "ports only_member", len(P1 - P2), "only_canon", len(P2 - P1),
          "body only_member", len(B1 - B2), "only_canon", len(B2 - B1))
    for x in list((P1 - P2))[:4] + list((P2 - P1))[:4] + list((B1 - B2))[:6] + list((B2 - B1))[:6]:
        print("   ", x[:220])
    # instance pin-level diff
    def conns(body):
        out = {}
        for s in body:
            mi = re.match(r"(\w+) (\w+) \((.*)\)$", s, re.S)
            if mi:
                for pn, ex in re.findall(r"\.(\w+)\(([^()]*)\)", mi.group(3)):
                    out[(mi.group(2), pn)] = ex.strip()
        return out
    c1 = {k: rn(v) for k, v in conns(mb).items()}; c2 = conns(cb)
    dif = [(k, c1.get(k), c2.get(k)) for k in sorted(set(c1) | set(c2)) if c1.get(k) != c2.get(k)]
    print("    inst pin diffs", len(dif), "of", len(c2))
    for d in dif[:12]:
        print("     ", d)
