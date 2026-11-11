import json, sys
from collections import defaultdict, deque
d = json.load(open(sys.argv[1])); m = d["modules"]["hc_top"]
cells = m["cells"]; names = {}
for n, nt in m["netnames"].items():
    for b in nt["bits"]:
        if isinstance(b, int) and (b not in names or len(n) < len(names[b])): names[b] = n
clk = set(m["ports"]["clk"]["bits"])
drv, loads = {}, defaultdict(list)
flops = {}
for cn, c in cells.items():
    t = c["type"]
    for p, bits in c["connections"].items():
        out = c.get("port_directions", {}).get(p) == "output"
        for b in bits:
            if not isinstance(b, int): continue
            (drv.__setitem__(b, (cn, p)) if out else loads[b].append((cn, p)))
    if "DFF" in t:
        cb = c["connections"]["C"][0]
        if cb in clk: flops[cn] = "neg" if "_N" in t.split("DFF")[1][:3] else "pos"
# BFS from each rclk flop Q through combinational cells to rclk flop D; count depth; report opposite-edge pairs
res = defaultdict(lambda: [0, 0])  # (src kind -> dst kind, src reg) -> [count, max depth]
for f, e in flops.items():
    q = cells[f]["connections"]["Q"][0]
    seen = {q: 0}; dq = deque([q])
    while dq:
        b = dq.popleft(); dep = seen[b]
        for cn, p in loads[b]:
            c = cells[cn]
            if cn in flops:
                if p == "D" and flops[cn] != e:
                    key = (e + "->" + flops[cn], names.get(q, "?").split(".")[-1].split("[")[0], names.get(c["connections"]["Q"][0], "?").split(".")[-1].split("[")[0])
                    r = res[key]; r[0] += 1; r[1] = max(r[1], dep)
                continue
            if "DFF" in c["type"]: continue
            for op, ob in c["connections"].items():
                if c.get("port_directions", {}).get(op) == "output":
                    for bb in ob:
                        if isinstance(bb, int) and bb not in seen: seen[bb] = dep + 1; dq.append(bb)
print(f"== {sys.argv[2]}: rclk flops pos {sum(1 for v in flops.values() if v=='pos')} neg {sum(1 for v in flops.values() if v=='neg')}")
for k, (n, dep) in sorted(res.items()):
    print(f"   {k[0]}  {k[1]} -> {k[2]}: {n} paths, max {dep} gate levels")
if not res: print("   no opposite-edge rclk paths")
