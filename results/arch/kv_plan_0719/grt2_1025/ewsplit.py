#!/usr/bin/env python3
"""PATH-KV-GRT2 what-if D: + E-W split of the per-row 1056-b slg rsp ft (pc -> hg ft3 -> hgi ftX -> pv) over two
horizontal core-free channels (upper half of the bits moved one channel: die y -319.68 = type +319.68 for MX rows 1-7).
usage: ewsplit.py PLAN ABS_DIR OUT_JSON"""
import json, re, sys, collections
from pathlib import Path
plan = json.load(open(sys.argv[1])); AD = Path(sys.argv[2])
parts = {p["name"]: p for p in plan["partitions"]}; T = plan["partition_types"]
SH = 319.68
todo = collections.defaultdict(set)
for pr in plan["ports"]:
    a, b = pr["src"]["part"], pr["dst"]["part"]
    for r in range(1, 8):
        if (a, b) == (f"hg_WN_{r}", f"hgi_WN_{r}") and pr["width"] >= 1000 and pr["face"] == "E":
            todo[parts[a]["type"]].add((pr["src"]["bus"][:-2], "both", pr["width"]))
            todo[parts[b]["type"]].add((pr["dst"]["bus"][:-2], "in", pr["width"]))
pinre = re.compile(r"  PIN (\S+)\[(\d+)\]\n((?:(?!  END ).*\n)*?)  END \1\[\2\]\n")
rectre = re.compile(r"(      LAYER (M\d) ;\n        RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;)")
rep = {}
for tn, items in todo.items():
    t = T[tn]; m = t["module"]; f = AD / f"{m}.lef"; s = f.read_text()
    cores = [(c["origin_um"][1], c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"] if c["outline_um"][0] > 100]
    repl = {}; bad = 0
    for pm in pinre.finditer(s):
        bus, bit = pm.group(1), int(pm.group(2))
        it = next((x for x in items if bus in (x[0] + "_i", x[0] + "_o") and (x[1] == "both" or bus.endswith("_i"))), None)
        if not it or bit < it[2] // 2: continue
        body = pm.group(0); r = rectre.search(body)
        y0, y1 = float(r.group(4)), float(r.group(6)); ny0, ny1 = y0 + SH, y1 + SH
        if any(a < ny1 and ny0 < b for a, b in cores): bad += 1
        nb = body[:r.start(4)] + f"{ny0:.4f}" + body[r.end(4):r.start(6)] + f"{ny1:.4f}" + body[r.end(6):]
        repl[pm.start()] = (pm.end(), nb)
    out, i = [], 0
    for st in sorted(repl): out += [s[i:st], repl[st][1]]; i = repl[st][0]
    out.append(s[i:]); f.write_text("".join(out)); rep[m] = dict(moved=len(repl), on_core=bad, slots=sorted(items))
json.dump(rep, open(sys.argv[3], "w"), indent=1); print(json.dumps(rep))
