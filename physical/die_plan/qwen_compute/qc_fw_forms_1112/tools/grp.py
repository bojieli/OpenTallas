import json, sys, re, collections
NAME = re.compile(r"(?:^|\.)(u_\w+?)(?:/|\.|\\?\[|$)")
def grp(n):
    n = n.replace("u_bound.", "")
    m = re.match(r"(u_core\.[a-z0-9_]+?)(?:\\?\[|\.|\$|/)", n)
    if m: return m.group(1)
    return re.split(r"[/\\\[]", n)[0]
d = json.load(open(sys.argv[1]))["pairs"]
c = collections.Counter(); mx = {}
for p in d:
    k = (grp(p["launch"]), grp(p["capture"]))
    c[k] += 1; mx[k] = max(mx.get(k, 0), p.get("um") or p.get("dist") or 0)
print(len(d), "pairs; keys", list(d[0].keys()))
for k, n in c.most_common(40):
    print(n, round(mx[k]), k)
