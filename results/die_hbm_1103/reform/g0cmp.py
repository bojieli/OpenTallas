"""cmp.py A B : ERROR message-set diff of two check.py reports (by check)."""
import json, sys, collections
def E(p):
    r = json.load(open(p))
    return collections.Counter((f["check"], f["msg"]) for f in r["findings"] if f["level"] == "ERROR")
a, b = E(sys.argv[1]), E(sys.argv[2])
ca = collections.Counter(k[0] for k in a.elements()); cb = collections.Counter(k[0] for k in b.elements())
print("by check:", {k: (ca[k], cb[k]) for k in sorted(set(ca) | set(cb))})
gone = a - b; new = b - a
print("gone", sum(gone.values()), "new", sum(new.values()))
n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
for k in list(new)[:n]: print("NEW", k[0], k[1][:300])
for k in list(gone)[:n]: print("GONE", k[0], k[1][:300])
