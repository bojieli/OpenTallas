import sys, json, collections
sys.path.insert(0, sys.argv[5] if len(sys.argv) > 5 else "py")
import common
S = common.parse_spec(sys.argv[1]); seg = json.load(open(sys.argv[2]))["seg_um"]
pred = json.load(open(sys.argv[3]))
par = {n: v["par"] for n, v in S["tree"].items()}; par.update({n: v["par"] for n, v in S["leaves"].items()})
def path(n):
    d = 0; L = 0
    while n != "root":
        d += 1; L += seg.get(n, 0); n = par[n]
    return d, L
st = collections.Counter(); rows = []
for n in S["leaves"]:
    d, L = path(n); st[d] += 1; rows.append((pred["TT_leaf"]["rise"][n] if "TT_leaf" in pred else 0, d, round(L, 1), n))
rows.sort()
print("depth hist", sorted(st.items()))
print("fastest", rows[:3]); print("slowest", rows[-3:])
