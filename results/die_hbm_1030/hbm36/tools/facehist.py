import sys, re, collections
W = float(sys.argv[2]); B = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
h = {"W": collections.Counter(), "E": collections.Counter()}
for ln in open(sys.argv[1]):
    m = re.search(r"-location \{([\d.]+) ([\d.]+)\}", ln)
    if not m: continue
    x, y = float(m[1]), float(m[2])
    f = "W" if x < 1 else ("E" if x > W - 1 else None)
    if f: h[f][int(y // B)] += 1
for f in "WE":
    tot = sum(h[f].values())
    print(f, tot, " ".join(f"{int(k*B)}:{v/B:.1f}" for k, v in sorted(h[f].items())))
