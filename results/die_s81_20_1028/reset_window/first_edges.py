"""Per register: the first clock edge (rst port asserted from an all-unknown power-up) at which lec.reset_state
proves it constant.  Uses the kit's own lec.py functions (read_aig/read_map/key_points/reset_vars/reset_state)."""
import sys, json, collections
sys.path.insert(0, sys.argv[1])
import lec
aig, amap, cycles, out = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
d = lec.read_aig(aig); m = lec.read_map(amap)
pis, cps, xs, anon, alias = lec.key_points(d, m)
lv = {}
R = lec.reset_vars(d, pis, None, lv)
st, first = lec.reset_state(d, R, cycles)
ffs = {k: lit for k, lit in pis.items() if k.startswith("ff:")}
fe = {}
for k, lit in ffs.items():
    v = lit >> 1
    if v in st:
        fe[k] = first.get(v)
# a register's 'first' is the LAST edge its value changed (reset_state updates first[v] each change) -> settled edge
hist = collections.Counter(fe.values())
late = sorted(((e, k) for k, e in fe.items() if e is not None and e > 4), reverse=True)
json.dump(dict(aig=aig, cycles=cycles, reset_ports=lv, n_ff=len(ffs), n_const=len(fe),
               hist={str(k): v for k, v in sorted(hist.items(), key=lambda x: (x[0] is None, x[0] or 0))},
               max_settle=max([e for e in fe.values() if e is not None], default=0),
               late=[[e, k] for e, k in late]), open(out, "w"), indent=0)
print(aig, "ports", lv, "ff", len(ffs), "const", len(fe), "hist", sorted(hist.items(), key=lambda x: x[0] or 0)[:40])
print("late(>4):", len(late), late[:15])
