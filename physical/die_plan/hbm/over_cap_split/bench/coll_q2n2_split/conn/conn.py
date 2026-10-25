# conn.py parent.json wrapper.sv out.json : per body_n2 WRAPPER port bit, the partners in the master parent view
# (excluded member cells u_ring/u_reduce/u_vmasm/u_writer, or master ports) -- PATH-HBM/NE2 10-25
import json, re, sys, collections
pj = json.load(open(sys.argv[1]))["modules"]["elab_top"]
REST = "coll_q2n2_body_rest"
cells = pj["cells"]
rest = [c for n, c in cells.items() if c["type"] == REST][0]
use = collections.defaultdict(set)
for n, c in cells.items():
    if c["type"] == REST:
        continue
    for p, bits in c["connections"].items():
        for b in bits:
            if isinstance(b, int):
                use[b].add("cell:" + n.lstrip("\\\\"))
for n, p in pj["ports"].items():
    for i, b in enumerate(p["bits"]):
        if isinstance(b, int):
            use[b].add("port:" + n)
# rest port bit -> partners
rp = {}
for p, bits in rest["connections"].items():
    rp[p] = [sorted(use.get(b, ())) if isinstance(b, int) else ["const"] for b in bits]
# wrapper: map extracted port (bit) -> wrapper port bit
txt = open(sys.argv[2]).read()
m = re.search(r"(?ms)\n    \S+_x u_x \((.*?)\);", txt)
wmap = collections.defaultdict(dict)
for pm in re.finditer(r"\.(\\\S+\s|[A-Za-z_][\w$]*)\s*\((.*?)\)\s*(?:,|$)", m.group(1), re.S):
    ep, ex = pm.group(1).strip().lstrip("\\\\"), pm.group(2).strip()
    mm = re.match(r"^([A-Za-z_]\w*)(?:\[(\d+)\])?$", ex)
    if not mm:
        continue
    wp, wi = mm.group(1), mm.group(2)
    if wp.endswith("__full"):
        continue
    src = rp.get(ep)
    if src is None:
        continue
    if wi is not None:
        wmap[wp][int(wi)] = src[0]
    else:
        for i, s in enumerate(src):
            wmap[wp][i] = s
# __full subsets (vm_rr / clk_reduce): wrapper bit k = master bit u[k]
for a in re.finditer(r"assign (\w+)__full\[(\d+)\] = (\w+)(?:\[(\d+)\])?;", txt):
    ep = a.group(1); src = rp.get(ep)
    if src:
        wmap[a.group(3)][int(a.group(4) or 0)] = src[int(a.group(2))]
out = {wp: [sorted(set(v[i])) for i in sorted(v)] for wp, v in wmap.items()}
json.dump(out, open(sys.argv[3], "w"))
summ = collections.Counter()
for wp, v in out.items():
    for s in v:
        summ[tuple(sorted(set(x.split(":")[0] + ":" + (x.split(":")[1].split(".")[-1] if x.startswith("cell") else re.sub(r"\d+", "#", x.split(":")[1])) for x in s)))] += 1
for k, n in summ.most_common(60):
    print(n, k)
print("wrapper ports mapped", len(out), "bits", sum(len(v) for v in out.values()))
