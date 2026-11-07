import json, sys, collections
O = sys.argv[1]
def load(d):
    r = json.load(open(f"{O}/chk_{d}/g0_report.json"))
    items = r.get("findings") or r.get("items") or r.get("errors") or r
    out = []
    def walk(x):
        if isinstance(x, dict):
            if "msg" in x or "message" in x:
                out.append(json.dumps({k: v for k, v in x.items()}, sort_keys=True).replace(f"{O}/{d}/", "DIR/"))
            else:
                for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(r)
    return collections.Counter(out)
a, b = load("base"), load("new")
gone, new = a - b, b - a
print("base", sum(a.values()), "new", sum(b.values()), "gone", sum(gone.values()), "NEW", sum(new.values()))
for k in list(new)[:20]: print("NEW", k[:400])
for k in list(gone)[:20]: print("GONE", k[:400])
