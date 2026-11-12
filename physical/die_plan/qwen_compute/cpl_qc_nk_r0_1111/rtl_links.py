"""CPL-QC-NK-R0: NK/NL core-to-core and core-to-bus links of a bound type body (bind rtl/<type>.sv), traced through
ot_dp_dly / ot_dp_dly_cnt chains, with total depth.  -> JSON rows {src, dst, depth, width}"""
import re, sys, json
sv = open(sys.argv[1]).read()
tiles = {}
for m in re.finditer(r"\n\s*(qfd_tile_n\w+)\s+u_u_t_(\d)_(\d)\s*\((.*?)\n\s*\);", sv, re.S):
    inst = f"u_t{m.group(2)}{m.group(3)}"
    ports = {pm.group(1): re.sub(r"\[.*?\]$", "", pm.group(2).strip()) for pm in re.finditer(r"\.(\w+)\((.*?)\)\s*,?\s*(?://.*)?\n", m.group(4) + "\n")}
    tiles[inst] = (m.group(1), ports)
dly = {}
for m in re.finditer(r"ot_dp_dly(?:_cnt)?\s*#\((.*?)\)\s*(\w+)\s*\((.*?)\);", sv, re.S):
    par, nm, body = m.groups()
    D = re.search(r"\.D\((\d+)\)", par); DM = re.search(r"\.DMAX\((\d+)\)", par)
    d = re.search(r"\.d\((.*?)\)\s*,\s*\.q", body).group(1); q = re.search(r"\.q\((.*?)\)\s*$", body.strip()).group(1)
    d = re.sub(r"\[.*?\]$", "", d.strip().strip("{}").split(",")[-1].strip()); q = re.sub(r"\[.*?\]$", "", q.strip().strip("{}").split(",")[-1].strip())
    dly[q] = (d, int(D.group(1)) if D else 0, f"+cnt<={DM.group(1)}" if DM else "", nm)
outs = {}
for t, (mod, ports) in tiles.items():
    for pn, net in ports.items():
        outs[net] = f"{t}.{pn}"
rows = []
for t, (mod, ports) in tiles.items():
    for pn, net in ports.items():
        if pn not in ("n_a", "n_b", "tap"):
            continue
        n, depth, cnt, chain = net, 0, "", []
        while n in dly:
            n, D, c, nm = dly[n]; depth += D; cnt += c; chain.append(nm)
        src = outs.get(n, n)
        rows.append(dict(dst=f"{t}.{pn}", src=src, depth=depth, cnt=cnt, chain=chain[::-1]))
for t, (mod, ports) in tiles.items():
    for pn in ("n_y", "t_out"):
        net = ports.get(pn)
        if net is None: continue
        users = [q for q, (d, *_ ) in dly.items() if d == net]
        for a in re.finditer(r"assign\s+(\w+)\s*=\s*" + re.escape(net) + r"\b", sv):
            rows.append(dict(src=f"{t}.{pn}", dst="out:" + a.group(1), depth=0, cnt="", chain=[]))
print(json.dumps(dict(tiles={t: m for t, (m, _) in tiles.items()}, links=rows), indent=1))
