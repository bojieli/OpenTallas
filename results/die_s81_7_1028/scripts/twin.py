import json, os, sys
O = sys.argv[1]; C = sys.argv[2]
t = json.load(open(f"{O}/clk_F/tree.json")); N = {int(k): v for k, v in t["nodes"].items()}
A = json.load(open(f"{O}/proof_F/tap_arrivals_{C}.json")); L = A["node_late_ps"]; ST = A["node_stages"]; XY = A["node_xy_um"]
def reg(R):
    taps = [x for x in A["taps"] if x["part"] == R]
    return os.path.commonprefix([x["tree_path"] for x in taps])
P3, P2 = reg("fE3_p2_b0"), reg("fE2_p2_b0")
sub3 = {p[len(P3):]: v for p, v in L.items() if p.startswith(P3)}
sub2 = {p[len(P2):]: v for p, v in L.items() if p.startswith(P2)}
rows = []
for s in sub3:
    if s and s in sub2 and s[:-1] in sub3 and s[:-1] in sub2:
        d3 = sub3[s] - sub3[s[:-1]]; d2 = sub2[s] - sub2[s[:-1]]
        rows.append((d3 - d2, s, round(d3, 1), round(d2, 1), ST[P3 + s] - ST[P3 + s[:-1]], [round(v) for v in XY[P3 + s]]))
rows.sort(key=lambda r: -abs(r[0]))
for r in rows[:15]: print("%+6.1f %-10s fE3 %6.1f fE2 %6.1f n %d xy3 %s" % r)
print("sum |d|", round(sum(abs(r[0]) for r in rows), 1), "legs", len(rows))
