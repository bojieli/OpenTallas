import sys, json, collections, re
# plan-placed control relays (reset/START relays, landing collector/origin) are excluded: their sites come from the plan reset/landing trees
src, out, b = sys.argv[1], sys.argv[2], 8.64
h = collections.Counter()
for l in open(src):
    f = l.split()
    if f[0] == "FF" and f[5] == "clk" and not re.search(r"u_(rrl|srl)_|u_cland_(collect|origin)", f[1]):
        x, y = float(f[3]), float(f[4]); h[(round((int(x // b) + .5) * b, 3), round((int(y // b) + .5) * b, 3))] += 1
json.dump({"bin_um": b, "source": src, "net": "clk", "bins": [[x, y, n] for (x, y), n in sorted(h.items())]}, open(out, "w"))
print(out, sum(h.values()), len(h))
