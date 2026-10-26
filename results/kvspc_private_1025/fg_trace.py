# trace port bits back through BUF/INV to the driving cell; print driver cell path and loads on each chain net
import sys, types, collections, re, json
src = open(sys.argv[1] + "/face_guard.py").read()
G = types.ModuleType("fg"); exec(compile(src, "fg", "exec"), G.__dict__)
mods = G.parse(open(sys.argv[2]).read())
used = {t for M in mods.values() for t, _, _ in M.cells}
top = [m for m in mods if m not in used][0]
F = G.Flat(mods, top)
drv, loads = collections.defaultdict(list), collections.defaultdict(list)
for ci, (m, path, pp) in enumerate(F.cells):
    for p, (d, bits) in pp.items():
        for b in bits:
            (drv if d == "out" else loads)[F.find(b)].append((ci, p))
def bufinv(m): return m.startswith("BUF") or m.startswith("INV") or m.startswith("HB")
out = {}
for b in sys.argv[3:]:
    r = F.find(b); chain = []
    while True:
        ds = drv[r]
        if len(ds) != 1: chain.append(("NODRV", r)); break
        ci, p = ds[0]; m, path, pp = F.cells[ci]
        ext = [(F.cells[c][0], F.cells[c][1], q) for c, q in loads[r] if not (chain and False)]
        chain.append((m, path, len(loads[r]), ext[:4]))
        if bufinv(m):
            r = F.find(pp["A"][1][0]); continue
        break
    print("==", b)
    for c in chain: print("   ", c)
