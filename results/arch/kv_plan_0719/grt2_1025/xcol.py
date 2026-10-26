#!/usr/bin/env python3
"""PATH-KV-GRT2 what-if C (kit level): W column N-S ft split over BOTH cored columns.
 hgi column keeps L350 (c1), L354 (c4), L663 bit-split over c2 + c3; hg column gets L751 (c1), L1524 (c2), L2048 (c3)
 as new straight N-S slots (ftw/ftx/fty) in hg/hg_v1/hg_v3 (rows hg_WN_0..7); L2045 leaves hgi_WN_7 (re-path via hub_C).
 Hub/IO E-W crossings of the re-pathed buses are NOT modelled (hub_Wo, io_W2/io_W3: analytic, see report).
usage: xcol.py PLAN ABS_DIR ROUTE_IN ROUTE_OUT OUT_JSON"""
import json, re, sys, collections
from pathlib import Path
plan = json.load(open(sys.argv[1])); AD = Path(sys.argv[2])
CH = [(0, 17.28), (233.28, 336.96), (552.96, 656.64), (872.64, 976.32), (1192.32, 1278.72)]
parts = {p["name"]: p for p in plan["partitions"]}; T = plan["partition_types"]
mod = lambda n: T[parts[n]["type"]]["module"]
P = {p["id"]: p for p in plan["ports"]}; L = {l["id"]: l for l in plan["lanes"]}
HGI = {f"hgi_WN_{r}" for r in range(8)} | {"hub_Wi", "io_W3"}
W = lambda lid: P[L[lid]["ports"][0]]["width"] + (1 if P[L[lid]["ports"][0]].get("epoch") else 0)
# hgi assignment: lane -> [(chan, nbits)]
HGI_A = {"L350": [(1, W("L350"))], "L663": [(2, W("L663") // 2), (3, W("L663") - W("L663") // 2)], "L354": [(4, W("L354"))]}
HG_A = {"L751": (1, "ftw"), "L1524": (2, "ftx"), "L2048": (3, "fty")}
pinre = re.compile(r"  PIN (\S+)\[(\d+)\]\n((?:(?!  END ).*\n)*?)  END \1\[\2\]\n")
rectre = re.compile(r"(      LAYER (M\d) ;\n        RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;)")
PG7 = [4.128, 4.512]
def m7_ok(x): return all(min((x - c) % 8.64, 8.64 - (x - c) % 8.64) > 0.25 for c in PG7)
def track(want, ln, used, a, b):
    pitch, off = (0.048, 0.024) if ln == "M5" else (0.064, 0.032)
    j0 = round((want - off) / pitch)
    for dd in range(0, 6000):
        for j in (j0 + dd, j0 - dd):
            x = off + j * pitch
            if a <= x <= b and round(x, 3) not in used[ln] and (ln != "M7" or m7_ok(x)):
                used[ln].add(round(x, 3)); return x
    raise SystemExit("no track")
rep = {"hgi": {}, "hg": {}}
# ---- hgi: move pins of the kept lanes into their assigned channel(s); spread per channel over [lo+0.6, hi-0.6]
ends = collections.defaultdict(set)
for lid in HGI_A:
    for pid in L[lid]["ports"]:
        pr = P[pid]
        if pr["face"] in "NS":
            for e in (pr["src"], pr["dst"]):
                if e["part"] in HGI: ends[(mod(e["part"]), e["bus"])].add(lid)
binch = {}
per_ch = collections.defaultdict(list)
for lid, al in HGI_A.items():
    b0 = 0
    for k, n in al:
        for b in range(b0, b0 + n): binch[(lid, b)] = k; per_ch[k].append((lid, b))
        b0 += n
for m in sorted({m for m, _ in ends}):
    f = AD / f"{m}.lef"; s = f.read_text(); H = float(re.search(r"SIZE [\d.]+ BY ([\d.]+) ;", s).group(1))
    used = collections.defaultdict(lambda: collections.defaultdict(set)); mv = []
    for pm in pinre.finditer(s):
        r = rectre.search(pm.group(3))
        if not r: continue
        x0, y0, x1, y1 = map(float, r.groups()[2:6]); face = "T" if y1 > H - 0.5 else ("B" if y0 < 0.5 else None)
        if face is None: continue
        bus, bit = pm.group(1), int(pm.group(2)); lids = ends.get((m, bus))
        if lids and (next(iter(lids)), bit) in binch: mv.append((pm, r, face, (next(iter(lids)), bit), x0, x1))
        else: used[face][r.group(2)].add(round((x0 + x1) / 2, 3))
    repl = {}
    for pm, r, face, lb, x0, x1 in mv:
        k = binch[lb]; a, b = CH[k][0] + 0.6, CH[k][1] - 0.6; idx = per_ch[k].index(lb); n = len(per_ch[k])
        x = track(a + (idx + 0.5) * (b - a) / n, r.group(2), used[face], a, b); hw = (x1 - x0) / 2; body = pm.group(0)
        r = rectre.search(body)
        nb = body[:r.start(3)] + f"{x - hw:.4f}" + body[r.end(3):r.start(5)] + f"{x + hw:.4f}" + body[r.end(5):]
        repl[pm.start()] = (pm.end(), nb)
    out, i = [], 0
    for st in sorted(repl): out += [s[i:st], repl[st][1]]; i = repl[st][0]
    out.append(s[i:]); f.write_text("".join(out)); rep["hgi"][m] = len(repl)
# ---- hg: new N-S slots, pins on both faces at the same x, alternating M5/M7, free tracks of the channel
for m in ("kv3_hg_part", "kv3_hg_v1_part", "kv3_hg_v3_part"):
    f = AD / f"{m}.lef"; s = f.read_text(); H = float(re.search(r"SIZE [\d.]+ BY ([\d.]+) ;", s).group(1))
    used = collections.defaultdict(set)
    for pm in pinre.finditer(s):
        r = rectre.search(pm.group(3))
        if r: used[r.group(2)].add(round((float(r.group(3)) + float(r.group(5))) / 2, 3))
    add = []
    for lid, (k, sl) in HG_A.items():
        n = W(lid); a, b = CH[k][0] + 0.6, CH[k][1] - 0.6
        for bit in range(n):
            ln = "M5" if bit % 2 == 0 else "M7"
            x = track(a + (bit + 0.5) * (b - a) / n, ln, used, a, b); hw = 0.012 if ln == "M5" else 0.016
            for nm, d_, (ya, yb) in ((f"{sl}_i[{bit}]", "INPUT", (H - 0.192, H)), (f"{sl}_o[{bit}]", "OUTPUT", (0.0, 0.192))):
                add.append(f"  PIN {nm}\n    DIRECTION {d_} ;\n    USE SIGNAL ;\n    PORT\n      LAYER {ln} ;\n"
                           f"        RECT {x - hw:.4f} {ya:.4f} {x + hw:.4f} {yb:.4f} ;\n    END\n  END {nm}\n")
    i = s.index("  OBS"); s = s[:i] + "".join(add) + s[i:]; f.write_text(s); rep["hg"][m] = len(add)
# ---- route netlist: drop hgi slots of the re-pathed lanes (+ L2045 in hgi_WN_7), add hg_WN_r slot nets
v = open(sys.argv[3]).read()
drop = collections.defaultdict(set)
for lid in list(HG_A) + ["L2045"]:
    for pid in L[lid]["ports"]:
        pr = P[pid]
        if pr["dst"]["part"] in {f"hgi_WN_{r}" for r in range(8)} and pr["dst"]["bus"].endswith("_i"):
            drop[pr["dst"]["part"]].add(pr["dst"]["bus"][:-2])
nd = 0
for part, sls in drop.items():
    i = v.index(f" {part} ("); j = v.index(");", i); seg = v[i:j]
    for sl in sls:
        w = f"ft_{part}__{sl}"; new = seg.replace(f", .{sl}_i({w}), .{sl}_o({w})", "")
        assert new != seg, (part, sl); seg = new; nd += 1
    v = v[:i] + seg + v[j:]
wires, nadd = [], 0
for r in range(8):
    part = f"hg_WN_{r}"; i = v.index(f" {part} ("); j = v.index(");", i); seg = v[i:j]
    for lid, (k, sl) in HG_A.items():
        w = f"ft_{part}__{sl}"; wires.append(f"  wire [{W(lid) - 1}:0] {w};"); seg += f", .{sl}_i({w}), .{sl}_o({w})"; nadd += 1
    v = v[:i] + seg + v[j:]
k = v.index("\n", v.index("input rst_n;")); v = v[:k + 1] + "\n".join(wires) + "\n" + v[k + 1:]
open(sys.argv[4], "w").write(v)
rep.update(dropped_slots=nd, added_slots=nadd,
           util_25={"hgi": {"c1": round((552 + 32) / 945, 3), "c2": round(522 / 945, 3), "c3": round(523 / 945, 3), "c4": round(174 / 787.6, 3)},
                    "hg": {"c1": round(549 / 945, 3), "c2": round(548 / 945, 3), "c3": round(523 / 945, 3)}})
json.dump(rep, open(sys.argv[5], "w"), indent=1); print(json.dumps(rep))
