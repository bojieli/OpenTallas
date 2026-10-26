#!/usr/bin/env python3
"""PATH-KV-GRT2 what-if: BIT-LEVEL water-fill of the W hgi column N-S ft buses over the core-free channels.
Moves the N/S face pins of the movable lanes' bits (hub_Wi N face, hgi_WN_0..7 both faces, io_W3 S face) so every bit
keeps ONE x through the column (straight, no jog) and every channel carries the same share.  Kit-level diagnostic only.
usage: wf_lef.py PLAN.json ABSTRACT_DIR OUT_JSON [--order L350,L354,L663,L751,L2048,L1524]"""
import json, re, sys, math, collections
from pathlib import Path
plan = json.load(open(sys.argv[1])); AD = Path(sys.argv[2])
ORDER = (sys.argv[4] if len(sys.argv) > 4 else "L350,L354,L663,L751,L2048,L1524").split(",")
CH = [(0, 17.28), (233.28, 336.96), (552.96, 656.64), (872.64, 976.32), (1192.32, 1278.72)]
CAP = 0.25 * (1 / 0.048 + 1 / 0.064)
X0 = 3179.52
parts = {p["name"]: p for p in plan["partitions"]}
mod = lambda n: plan["partition_types"][parts[n]["type"]]["module"]
P = {p["id"]: p for p in plan["ports"]}; L = {l["id"]: l for l in plan["lanes"]}
COLPARTS = {f"hgi_WN_{r}" for r in range(8)} | {"hub_Wi", "io_W3"}
width = {lid: P[L[lid]["ports"][0]]["width"] for lid in ORDER}
# ends to edit: (module, pin bus) -> lane
ends = collections.defaultdict(set)
for lid in ORDER:
    for pid in L[lid]["ports"]:
        pr = P[pid]
        if pr["face"] not in "NS": continue
        for e in (pr["src"], pr["dst"]):
            if e["part"] in COLPARTS: ends[(mod(e["part"]), e["bus"])].add(lid)
# fixed loads per channel (all other ports crossing hgi_WN_3|4)
fixed = [0] * len(CH)
for pr in plan["ports"]:
    if {pr["src"]["part"], pr["dst"]["part"]} != {"hgi_WN_3", "hgi_WN_4"}: continue
    lid = next(l for l in L if pr["id"] in L[l]["ports"]) if False else None
lane_of = {p: l["id"] for l in plan["lanes"] for p in l["ports"]}
for pr in plan["ports"]:
    if {pr["src"]["part"], pr["dst"]["part"]} != {"hgi_WN_3", "hgi_WN_4"} or lane_of[pr["id"]] in ORDER: continue
    m = sum(pr["window_um"]) / 2 - X0
    fixed[next(i for i, (u, v) in enumerate(CH) if u - 1 <= m <= v + 1)] += pr["width"]
tot = sum(width.values())
lo, hi = 0.0, 2.0
for _ in range(60):
    u = (lo + hi) / 2
    room = sum(max(0, (v - a) * CAP * u - f) for (a, v), f in zip(CH, fixed))
    lo, hi = (u, hi) if room < tot else (lo, u)
u = hi
rooms = [max(0, (v - a) * CAP * u - f) for (a, v), f in zip(CH, fixed)]
# sequential fill (fewest splits)
seq = [(lid, b) for lid in ORDER for b in range(width[lid])]
chan_bits = [[] for _ in CH]; k = 0; acc = 0.0
for i, lb in enumerate(seq):
    while k < len(CH) - 1 and len(chan_bits[k]) >= round(rooms[k]): k += 1
    chan_bits[k].append(lb)
target_ch = {lb: k for k, cb in enumerate(chan_bits) for lb in cb}
summary = dict(u_target=round(u, 3), fixed=fixed, rooms=[round(r) for r in rooms],
               chan=[dict(ch=CH[k], fixed=fixed[k], moved=len(cb), util=round((fixed[k] + len(cb)) / ((CH[k][1] - CH[k][0]) * CAP), 3),
                          lanes=dict(collections.Counter(l for l, _ in cb))) for k, cb in enumerate(chan_bits)])
PG7 = [4.128, 4.512]
def m7_ok(x): return all(abs(((x - c) % 8.64 + 8.64) % 8.64) > 0.25 and abs(((x - c) % 8.64) - 8.64) > 0.25 for c in PG7)
pinre = re.compile(r"  PIN (\S+)\[(\d+)\]\n((?:(?!  END ).*\n)*?)  END \1\[\2\]\n")
rectre = re.compile(r"(      LAYER (M\d) ;\n        RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;)")
edited = collections.Counter()
for m in sorted({m for m, _ in ends}):
    f = AD / f"{m}.lef"; s = f.read_text()
    H = float(re.search(r"SIZE [\d.]+ BY ([\d.]+) ;", s).group(1))
    pins = []  # (start,end,bus,bit,layer,x0,y0,x1,y1)
    for pm in pinre.finditer(s):
        r = rectre.search(pm.group(3))
        if not r: continue
        x0, y0, x1, y1 = map(float, r.groups()[2:6])
        face = "T" if y1 > H - 0.5 else ("B" if y0 < 0.5 else None)
        pins.append((pm, pm.group(1), int(pm.group(2)), r.group(2), x0, y0, x1, y1, face))
    # used tracks per (face, layer) by non-moved pins
    used = collections.defaultdict(set); mv = collections.defaultdict(list)
    for (pm, bus, bit, ln, x0, y0, x1, y1, face) in pins:
        if face is None: continue
        lids = ends.get((m, bus))
        if lids and (next(iter(lids)), bit) in target_ch:
            lid = next(iter(lids)); mv[(face, target_ch[(lid, bit)])].append((pm, bus, bit, ln, x0, y0, x1, y1, (lid, bit)))
        else:
            used[(face, ln)].add(round((x0 + x1) / 2, 3))
    repl = {}
    for (face, k), lst in mv.items():
        a, b = CH[k]; a += 0.6; b -= 0.6
        order = {lb: j for j, lb in enumerate(chan_bits[k])}
        lst.sort(key=lambda t: order[t[8]]); n = len(chan_bits[k])
        for t in lst:
            pm, bus, bit, ln, x0, y0, x1, y1, lb = t
            want = a + (order[lb] + 0.5) * (b - a) / n
            pitch, off = (0.048, 0.024) if ln == "M5" else (0.064, 0.032)
            j0 = round((want - off) / pitch)
            for d in range(0, 4000):
                for j in (j0 + d, j0 - d):
                    x = off + j * pitch
                    if a <= x <= b and round(x, 3) not in used[(face, ln)] and (ln != "M7" or m7_ok(x)): break
                else: continue
                break
            used[(face, ln)].add(round(x, 3)); hw = (x1 - x0) / 2
            body = pm.group(0)
            r = rectre.search(body)
            nb = body[:r.start(3)] + f"{x - hw:.4f}" + body[r.end(3):r.start(5)] + f"{x + hw:.4f}" + body[r.end(5):]
            repl[pm.start()] = (pm.end(), nb); edited[m] += 1
    out = []; i = 0
    for st in sorted(repl):
        en, nb = repl[st]; out.append(s[i:st]); out.append(nb); i = en
    out.append(s[i:]); f.write_text("".join(out))
summary["edited_pins"] = dict(edited)
json.dump(summary, open(sys.argv[3], "w"), indent=1); print(json.dumps(summary))
