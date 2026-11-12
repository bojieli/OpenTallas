"""DIE-PROTO-1: (launch tap, capture tap) per HEAD seam group: trace each worst-hold flop's clock pin back to its part clock port."""
import csv, json, sys, re
sys.path.insert(0, sys.argv[1])
import die_sta as D
I, rows_tsv, out = sys.argv[2:5]
inst = json.load(open(I + "/run_tree2nm/die_sta.json"))["instances"]
cache = {}
def part(m):
    if m not in cache:
        nl = next(iter(D.read_verilog(f"{I}/run_tree2nm/ilm/{m}/6_final.v").values()))
        drv, pins = {}, {}
        for cell, i, conns in nl.insts:
            pins[i] = (cell, dict(conns))
            for p, bits in conns:
                if p in ("Y", "QN", "Q") and bits:
                    drv[bits[0]] = (i, cell)
        ports = {n for d, n, *_ in nl.ports if d == "input"}
        cache[m] = (drv, pins, ports)
    return cache[m]
def tap(pin_path):
    i, rest = pin_path.split("/", 1)
    fl = rest.rsplit("/", 1)[0]
    drv, pins, ports = part(inst[i])
    if fl not in pins:
        return None
    net = pins[fl][1].get("CLK", [None])[0]
    for _ in range(200):
        if net is None:
            return None
        base = net.split("[")[0]
        if net in ports or base in ports:
            return f"{i}/{net}"
        d = drv.get(net)
        if d is None:
            return None
        c = pins[d[0]][1]
        net = (c.get("A") or c.get("CLK") or [None])[0]
    return None
res = []
for r in csv.DictReader(open(rows_tsv), delimiter="\t"):
    if r["cls"] != "seam" or r["hold_start"] in ("None", ""):
        continue
    g = r["group"]
    if not re.match(r"sp\d", g):
        continue
    res.append(dict(group=g, hold_FF=float(r["hold_FF"]), launch_flop=r["hold_start"], capture_flop=r["hold_end"],
                    launch_tap=tap(r["hold_start"]), capture_tap=tap(r["hold_end"])))
json.dump(res, open(out, "w"), indent=1)
for x in sorted(res, key=lambda x: x["hold_FF"])[:30]:
    print(x["group"], x["hold_FF"], x["launch_tap"], x["capture_tap"])
