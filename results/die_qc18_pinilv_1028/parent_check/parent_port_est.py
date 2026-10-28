"""DIE-QC-18-PINILV parent n_a/n_b/n_y strip track check (estimate, no rebuild).  Inputs: node pin tables (old/ilv), trace2.txt
(A0 parent nk 3_place: every 4th bit of node a/b -> parent face register -> its upstream port buffer; y -> parent register -> port
buffer).  Node instance MY at (394.416, 688.656): parent y = 688.656 + local y.  Output: sum of vertical port->pin distance and the
horizontal-cut demand along the node face (x4 for all bits)."""
import re, statistics as S, json
Y0 = 688.656
old = {q["name"]: q["y"] for q in json.load(open("node_pins.json"))["pins"]}
new = {q["name"]: q["y"] for q in json.load(open("node_pins_ilv.json"))["pins"]}
src = {}
for l in open("trace2.txt"):
    t = l.split(); m = re.search(r"(input|output)\d+@([\d.]+),([\d.]+)", l)
    src[f"{t[0]}[{t[1]}]"] = float(m.group(3)) if m else None
names = [k for k in src if src[k] is not None]
ys = [src[n] for n in names]
print(f"traced bits {len(src)}, with port buffer {len(names)}; port-buffer parent y min/median/max {min(ys):.1f}/{S.median(ys):.1f}/{max(ys):.1f}"
      f" (node spans {Y0:.1f}-{Y0+432:.1f}); south of node: {sum(y < Y0 for y in ys)}")
for lab, P in (("a0k3 bands", old), ("a0k6 per-adder", new)):
    L = [abs(Y0 + P[n] - src[n]) for n in names]
    cuts = {c: 4 * sum(min(Y0 + P[n], src[n]) < Y0 + c < max(Y0 + P[n], src[n]) for n in names) for c in range(0, 432, 25)}
    print(f"{lab}: sum|dy| x4 = {4*sum(L):.0f} um (mean {S.mean(L):.1f}); cut demand x4 by local y: {cuts}; max {max(cuts.values())}")
