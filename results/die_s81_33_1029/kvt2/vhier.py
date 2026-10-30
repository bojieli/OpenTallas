import json, sys, collections
d = json.load(open(sys.argv[1]))
MAC = sys.argv[2].split(",")
mods = {}
def walk(n, cur=None, scope=""):
    if isinstance(n, dict):
        t = n.get("type")
        if t == "MODULE":
            cur = n["addr"]; mods[cur] = [n.get("name"), n.get("origName"), []]; scope = ""
        elif t in ("BEGIN", "GENBLOCK") and n.get("name") and cur is not None:
            scope = scope + n["name"] + "."
        elif t == "CELL" and cur is not None:
            mods[cur][2].append((scope + n.get("name"), n.get("modp")))
        for k, v in n.items():
            if isinstance(v, (list, dict)):
                walk(v, cur, scope)
    elif isinstance(n, list):
        for x in n: walk(x, cur, scope)
walk(d)
top = [a for a, v in mods.items() if v[0] == sys.argv[3]]
assert top, "top missing"
out = collections.Counter(); rows = []
def rec(a, path):
    for cn, mp in mods[a][2]:
        if mp not in mods: continue
        cnm, corig, _ = mods[mp]
        base = corig or cnm
        hit = [m for m in MAC if base == m or base.startswith(m + "__")]
        if hit:
            out[hit[0]] += 1; rows.append((path + cn, hit[0]))
        else:
            rec(mp, path + cn + ".")
rec(top[0], "")
print("#", dict(out), sum(out.values()))
for p, m in rows: print(p, m)
