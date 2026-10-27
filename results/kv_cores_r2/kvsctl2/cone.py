import json, re, sys, collections
J = json.load(open(sys.argv[1])); M = J["modules"]["qkd_kvs_ctl"]; rep = json.load(open(sys.argv[2]))
cells = M["cells"]; ports = M["ports"]
drv = {}
for cn, c in cells.items():
    for p, bits in c["connections"].items():
        if c["port_directions"].get(p) == "output":
            for i, b in enumerate(bits):
                if isinstance(b, int): drv[b] = (cn, p, i)
pin = {}
for pn, p in ports.items():
    if p["direction"] == "input":
        for i, b in enumerate(p["bits"]):
            pin[b] = f"{pn}[{i}]"
FFT = {"$dff", "$adff", "$dffe", "$adffe", "$sdff", "$sdffe", "$sdffce", "$aldff", "$aldffe", "$dffsr", "$dffsre"}
def cone(b):
    leaves = collections.Counter(); seen = set(); st = [b]; ncell = 0; roots = set()
    while st:
        x = st.pop()
        if not isinstance(x, int) or x in seen: continue
        seen.add(x)
        if x in pin: leaves["IN:" + re.sub(r"\[\d+\]$", "", pin[x])] += 1; continue
        d = drv.get(x)
        if d is None: leaves["undriven"] += 1; continue
        c = cells[d[0]]
        if c["type"] in FFT or c["type"].startswith("$mem") or "sram" in c["type"]:
            leaves[c["type"] + ":" + re.sub(r"\.[^.]*$", "", d[0])[-60:]] += 1; continue
        ncell += 1
        for p, bits in c["connections"].items():
            if c["port_directions"].get(p) == "input": st.extend(bits)
    return leaves, ncell
groups = collections.defaultdict(list)
for x in rep[sys.argv[3]]:
    m = re.match(r"(.*?)\[(\d+)\]", x); groups[m[1]].append(int(m[2]))
for pn, bits in groups.items():
    p = ports[pn]
    if p["direction"] == "output":
        b = p["bits"][bits[0]]; d = drv[b]; src = cells[d[0]]["attributes"].get("src", "")
        lv, n = cone(b)
        print(pn, len(bits), "root", cells[d[0]]["type"], src.split("/")[-1][:80], "cells", n, dict(list(lv.items())[:6]))
    else:
        b = p["bits"][bits[0]]
        ld = [(cn, pp) for cn, c in cells.items() for pp, bb in c["connections"].items() if c["port_directions"].get(pp) == "input" and b in bb]
        for cn, pp in ld[:2]:
            print(pn, len(bits), "load", cells[cn]["type"], pp, cells[cn]["attributes"].get("src", "").split("/")[-1][:80])
