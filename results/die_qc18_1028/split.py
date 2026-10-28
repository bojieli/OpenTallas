# DIE-QC-18: split cluster a0cl47 (tall 39x129 um box, root at its S end -> 38 ps local CTS width) into two
# clusters by median y; each root at its registers centroid. Output cl_nk.json (in place copy) + split.log
import json, re, statistics as st, sys
G = json.load(open("cl_nk.json")); name = sys.argv[1] if len(sys.argv) > 1 else "a0cl47"
c = [c for c in G["clusters"] if c["name"] == name][0]
want = set(r.replace("\\", "") for r in c["regs"]); pos = {}
comp = False
for l in open("cl_nk.def"):
    if l.startswith("COMPONENTS"): comp = True; continue
    if l.startswith("END COMPONENTS"): break
    if comp and l.lstrip().startswith("-"):
        p = l.split(); n = p[1].replace("\\", "")
        if n in want:
            m = re.search(r"\( (-?\d+) (-?\d+) \)", l)
            pos[n] = (int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0)
assert len(pos) == len(want), (len(pos), len(want))
regs = sorted(c["regs"], key=lambda r: pos[r.replace("\\", "")][1])
h = len(regs) // 2; parts = [regs[:h], regs[h:]]
new = max(int(x["name"][4:]) for x in G["clusters"]) + 1
out = []
for k, rs in enumerate(parts):
    xs = [pos[r.replace("\\", "")][0] for r in rs]; ys = [pos[r.replace("\\", "")][1] for r in rs]
    nm = name if k == 0 else "a0cl%d" % new
    out.append(dict(name=nm, n=len(rs), root=[round(st.mean(xs), 3), round(st.mean(ys), 3)],
                    box=[min(xs), min(ys), max(xs), max(ys)], regs=rs))
    print(nm, len(rs), out[-1]["root"], out[-1]["box"])
i = G["clusters"].index(c); G["clusters"][i:i + 1] = out
json.dump(G, open("cl_nk.json", "w"))
print("clusters", len(G["clusters"]))
