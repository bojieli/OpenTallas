import sys, collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
csv, png, title = sys.argv[1], sys.argv[2], sys.argv[3]
pts = collections.defaultdict(list); die=None; area=collections.Counter(); n=collections.Counter()
for l in open(csv):
    a = l.strip().split(",")
    if a[0] == "#die": die = list(map(float, a[1:])); continue
    m, x, y, ar = a[0], float(a[1]), float(a[2]), float(a[3])
    k = "pin" if m.startswith("PIN:") else "HB4 (hold)" if m.startswith("HB") else "flop" if m.startswith(("DFF","DHL","SDF","ASYNC")) else "clock buf" if ("clkbuf" in m.lower() or m.startswith("BUFx24") ) else "other"
    pts[k].append((x, y)); area[k]+=ar; n[k]+=1
fig, ax = plt.subplots(figsize=(10, 12), dpi=130)
col = {"pin": "black", "HB4 (hold)": "red", "flop": "tab:blue", "other": "tab:green", "clock buf": "orange"}
for k in ("other", "flop", "clock buf", "HB4 (hold)", "pin"):
    if pts[k]:
        xs, ys = zip(*pts[k]); ax.scatter(xs, ys, s=0.4 if k!="pin" else 0.2, c=col[k], label=f"{k} {n[k]}", linewidths=0)
if die: ax.add_patch(plt.Rectangle((die[0],die[1]),die[2]-die[0],die[3]-die[1],fill=False,ec="k"))
ax.set_aspect("equal"); ax.legend(markerscale=12, loc="upper right"); ax.set_title(title)
fig.savefig(png, bbox_inches="tight"); 
print(dict(n), {k: round(v,1) for k,v in area.items()}, "die", die)
