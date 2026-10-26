#!/usr/bin/env python3
"""PATH-KV-GRT2 what-if: E-W split of EVERY >=1000-b hg_X_r -> hgi_X_r ft hop (rows 0-7, W and E columns): the upper
half of the bits moves one core-row channel (+-319.68 um in type frame, sign picked to stay core-free) on both the hg
out pin and the hgi in pin.  usage: ewsplit2.py PLAN ABS_DIR OUT_JSON"""
import json, re, sys, collections
from pathlib import Path
plan = json.load(open(sys.argv[1])); AD = Path(sys.argv[2])
parts = {p["name"]: p for p in plan["partitions"]}; T = plan["partition_types"]
todo = collections.defaultdict(set)
for pr in plan["ports"]:
    a, b = pr["src"]["part"], pr["dst"]["part"]
    if a.startswith("hg_") and b == "hgi_" + a[3:] and pr["width"] >= 1000 and pr["dst"]["bus"].startswith("ft"):
        todo[parts[a]["type"]].add((pr["src"]["bus"][:-2], pr["width"])); todo[parts[b]["type"]].add((pr["dst"]["bus"][:-2], pr["width"]))
pinre = re.compile(r"  PIN (\S+)\[(\d+)\]\n((?:(?!  END ).*\n)*?)  END \1\[\2\]\n")
rectre = re.compile(r"(      LAYER (M\d) ;\n        RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;)")
rep = {}
for tn, items in todo.items():
    t = T[tn]; m = t["module"]; f = AD / f"{m}.lef"; s = f.read_text(); H = t["outline_um"][1]
    cores = [(c["origin_um"][1] - 2, c["origin_um"][1] + c["outline_um"][1] + 2) for c in t["hard_cores"] if c["outline_um"][0] > 100]
    hit = lambda y0, y1: any(a < y1 and y0 < b for a, b in cores)
    repl = {}; bad = 0; sh = collections.Counter()
    for pm in pinre.finditer(s):
        bus, bit = pm.group(1), int(pm.group(2))
        it = next((x for x in items if bus in (x[0] + "_i", x[0] + "_o")), None)
        if not it or bit < it[1] // 2: continue
        body = pm.group(0); r = rectre.search(body); y0, y1 = float(r.group(4)), float(r.group(6))
        if float(r.group(3)) > 0.5 and float(r.group(5)) < t["outline_um"][0] - 0.5: continue   # not a face pin
        for SH in (319.68, -319.68):
            if 0 < y0 + SH < H and not hit(y0 + SH, y1 + SH): break
        else: bad += 1; continue
        sh[(bus, SH)] += 1
        nb = body[:r.start(4)] + f"{y0 + SH:.4f}" + body[r.end(4):r.start(6)] + f"{y1 + SH:.4f}" + body[r.end(6):]
        repl[pm.start()] = (pm.end(), nb)
    out, i = [], 0
    for st in sorted(repl): out += [s[i:st], repl[st][1]]; i = repl[st][0]
    out.append(s[i:]); f.write_text("".join(out)); rep[m] = dict(moved=len(repl), no_room=bad, shifts={f"{k[0]}{k[1]:+}": v for k, v in sh.items()})
json.dump(rep, open(sys.argv[3], "w"), indent=1); print(json.dumps(rep))
