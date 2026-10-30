import json, re, sys, collections
d = json.load(open(sys.argv[1]))
L = d["lanes"]["unplanned_bit_list"]
def pre(s, n=3):
    s = re.sub(r"\[\d+\]", "", s)
    parts = s.split(".")
    return ".".join(parts[:n])
G = collections.defaultdict(collections.Counter)
for b in L:
    if not b["src_part"].startswith("NE") and b["src_part"] != "root": continue
    k = f'{b["src_part"]}->{b["dst_part"]}'
    sk = pre(b["sink_ports"][0]) if b["sink_ports"] else "-"
    G[k][(pre(b["driver"]), sk)] += 1
tot = {k: sum(v.values()) for k, v in G.items()}
for k in sorted(G, key=lambda k: -tot[k]):
    print(f"{k}  {tot[k]}")
    for (a, s), n in G[k].most_common(4):
        print(f"     {n:5d}  {a}  ->  {s}")
