"""per-net driver->load resistance (shortest resistor path) from a SPEF; report load-R asymmetry per net level."""
import sys, re, collections, heapq, json
spef, out = sys.argv[1], sys.argv[2]
nm = {}; f = open(spef); sec = None; res = {}
lines = f.read().split("\n")
i = 0
while i < len(lines) and not lines[i].startswith("*NAME_MAP"): i += 1
i += 1
while i < len(lines) and re.match(r"\*\d+ ", lines[i]):
    a, b = lines[i].split()[:2]; nm[a] = b; i += 1
rows = []
while i < len(lines):
    l = lines[i]
    if l.startswith("*D_NET"):
        name = nm.get(l.split()[1], l.split()[1]); i += 1
        conn, R, mode = [], [], None
        while not lines[i].startswith("*END"):
            s = lines[i].strip(); p = s.split()
            if s.startswith("*CONN"): mode = "n"
            elif s.startswith("*CAP"): mode = "c"
            elif s.startswith("*RES"): mode = "r"
            elif mode == "n" and p and p[0] == "*I": conn.append((p[1], p[2]))
            elif mode == "r" and len(p) == 4: R.append((p[1], p[2], float(p[3])))
            i += 1
        if name.startswith("ckm_w_ckm_") and R:
            G = collections.defaultdict(list)
            for a, b, r in R: G[a].append((b, r)); G[b].append((a, r))
            drv = [c for c, d in conn if d == "O"]; lds = [c for c, d in conn if d == "I"]
            if drv:
                dist = {drv[0]: 0.0}; h = [(0.0, drv[0])]
                while h:
                    x, u = heapq.heappop(h)
                    if x > dist[u]: continue
                    for v, r in G[u]:
                        if x + r < dist.get(v, 1e18): dist[v] = x + r; heapq.heappush(h, (x + r, v))
                rl = [dist.get(c) for c in lds if c in dist]
                if len(rl) >= 2:
                    rows.append((name, min(rl), max(rl), len(rl)))
    i += 1
lv = collections.defaultdict(list)
for n, a, b, k in rows:
    m = re.match(r"ckm_w_ckm_([nrt])(\d+)", n); lv[(m.group(1) + m.group(2)) if m else n[:12]].append((b - a, a, b, n))
rep = {}
for k in sorted(lv):
    v = sorted(lv[k]); rep[k] = dict(nets=len(v), max_dR=round(v[-1][0], 1), med_dR=round(v[len(v)//2][0], 1), worst=v[-1][3])
    print(k, rep[k])
json.dump(rep, open(out, "w"), indent=1)
