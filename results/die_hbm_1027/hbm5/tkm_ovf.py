import re, sys, collections, statistics as st
G = sys.argv[1]
cells, pins = {}, {}
for ln in open(G):
    f = ln.rstrip("\n").split("\t")
    if f[0] == "C": cells[f[-1]] = (f[2], (float(f[4]) + float(f[6])) / 2, (float(f[5]) + float(f[7])) / 2)
    elif f[0] == "P": pins[f[2]] = (float(f[6]), float(f[7]))
ib = {int(re.search(r"\[(\d+)\]", n)[1]): v for n, v in pins.items() if n.startswith("tile_ins_b[")}
ob = {int(re.search(r"\[(\d+)\]", n)[1]): v for n, v in pins.items() if n.startswith("tile_ovf_b[")}
print("ins_b==ovf_b x for all bits:", all(abs(ib[k][0] - ob[k][0]) < 1e-3 for k in ib), "ovf_b y", set(round(v[1], 2) for v in ob.values()))
ins_order = [k for k, _ in sorted(ib.items(), key=lambda kv: kv[1][0])]; print("ins_b x-order == bit order:", ins_order == sorted(ins_order), ins_order[:12])
outs = [n for n in cells if "ovf_b" in n and cells[n][0] == "S"][:5]; print("ovf_b flops sample", outs)
# p_bg column centroid per bit vs ovf-related flops
col = collections.defaultdict(list)
for n, (k_, x, y) in cells.items():
    m = re.match(r"u_fcore\.u_core\.u_tile\.u\.[pq]_bg\\\[(\d+)\\\]\\\[(\d+)\\\]", n)
    if m: col[int(m[2])].append(x)
cx = {k: st.median(v) for k, v in col.items()}
print("bits with columns", len(cx), "col x range", round(min(cx.values()), 1), round(max(cx.values()), 1))
ordc = [k for k, _ in sorted(cx.items(), key=lambda kv: kv[1])]; print("column x-order head", ordc[:20])
inv = sum(1 for i in range(len(ordc)) for j in range(i + 1, len(ordc)) if ordc[i] > ordc[j]); print("inversions vs bit order", inv, "of", len(ordc) * (len(ordc) - 1) // 2)
print("|pin x - column x| max/median", round(max(abs(ib[k][0] - cx[k]) for k in cx), 1), round(st.median(abs(ib[k][0] - cx[k]) for k in cx), 1))
# structural rule test: interleaved slot
def rank(L):
    o = sorted(range(len(L)), key=lambda i: L[i]); r = [0] * len(L)
    for i, j in enumerate(o): r[j] = i
    return r
ks = sorted(cx)
for name, f in (("bit order", lambda k: k), ("interleave4x86", lambda k: 4 * (k % 86) + k // 86)):
    a = rank([cx[k] for k in ks]); b = rank([f(k) for k in ks]); n = len(ks)
    rho = 1 - 6 * sum((x - y) ** 2 for x, y in zip(a, b)) / (n * (n * n - 1))
    # predicted pin x: slot spread uniformly over the current pin x range
    xs = sorted(v[0] for v in ib.values()); px = {k: xs[f(k) if name != "bit order" else k] for k in ks}
    d = [abs(px[k] - cx[k]) for k in ks]
    print(name, "spearman", round(rho, 3), "|pin-col| max/p90/median", round(max(d), 1), round(sorted(d)[int(.9 * n)], 1), round(st.median(d), 1))
