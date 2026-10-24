"""CB16 alignment with fabric shifts: sigma(u_x) over the fabric (max over non-constant inputs), tile t_out = sigma(tap
source) + edge offset, node n_y = later of n_a / n_b; report the n_a / n_b skew per node and the pads needed."""
import json, re, sys
from collections import defaultdict
bdir, cl = sys.argv[1], sys.argv[2]
sinks = json.load(open(bdir + "/bind_sinks.json"))
bg = json.load(open(bdir + "/bus_groups.json"))
asb = {}
for g in bg["landing"]:
    if not g["sink"].startswith(cl + "."):
        continue
    for m in g["members"]:
        for i in [i for a, b in m["sink_bits"] for i in range(a, b + 1)]:
            asb[(g["sink"], m["sink_port"], i)] = m["asbuilt_stages"]
inp = defaultdict(dict)   # leaf -> port -> (src leaf, src port, offset)
for k, v in sinks.items():
    if not k.startswith(cl + ".") or v[0] != "pin":
        continue
    lp, bit = k.rsplit("[", 1)
    leaf, port = lp.rsplit(".", 1)
    if port in ("tile_id", "rst_n", "sidx") or "tie" in v[1]:
        continue
    b = int(bit[:-1])
    sl, sp = v[1].rsplit("[", 1)[0].rsplit(".", 1)
    a = asb.get((leaf, port, b))
    off = 0 if a is None else v[2] - a
    cur = inp[leaf].get(port)
    if cur is None or off > cur[2]:
        inp[leaf][port] = (sl, sp, off)
memo = {}
def sig(leaf, port_out, depth=0):
    key = (leaf, port_out)
    if key in memo:
        return memo[key]
    if depth > 60 or leaf not in inp:
        return 0
    memo[key] = 0
    ins = inp[leaf]
    if ".u_t_" in leaf:
        if port_out == "t_out":
            s = ins.get("tap")
            r = sig(s[0], s[1], depth + 1) + s[2] if s else 0
        else:
            xs = [sig(s[0], s[1], depth + 1) + s[2] for p, s in ins.items() if p in ("n_a", "n_b")]
            r = max(xs) if xs else 0
    else:
        xs = [sig(s[0], s[1], depth + 1) + s[2] for p, s in ins.items()]
        r = max(xs) if xs else 0
    memo[key] = r
    return r
tot = 0
for leaf in sorted(inp):
    if ".u_t_" in leaf and "n_a" in inp[leaf] and "n_b" in inp[leaf]:
        a = inp[leaf]["n_a"]; b = inp[leaf]["n_b"]
        sa = sig(a[0], a[1]) + a[2]; sb = sig(b[0], b[1]) + b[2]
        tot += abs(sa - sb) * 514
        print(leaf.split(".")[-1], "n_a", a[0].split(".")[-1], a[1], sa, "n_b", b[0].split(".")[-1], b[1], sb, "skew", sa - sb)
for leaf in sorted(inp):
    if ".u_t_" in leaf:
        s = inp[leaf].get("tap")
        print(" ", leaf.split(".")[-1], "tap", s and (s[0].split(".")[-1], s[2]), "t_out sigma", sig(leaf, "t_out"))
print("pad flops", tot)
