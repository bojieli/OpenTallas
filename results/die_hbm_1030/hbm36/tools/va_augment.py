#!/usr/bin/env python3
"""DIE-HBM-36 V-A G2 probe builder: copy a stock g2.py part probe dir (q_b010 on d35a) and add NB synthetic
through bits (type E face -> type W face) inside the core-free EW FT corridor [Y0, Y1], interleaved on free M4/M6
tracks between the existing pins, so the face density reaches the 12-pins/um V-A budget; each bit = 3-station chain
(st0 beside the in pin, st1 at X1, st2 at X2; hops <= 405 um) like a plan ft slot.  Diagnostic only, never writes the plan.
usage: va_augment.py SRC_PROBE_DIR DST_DIR NB Y0 Y1 [X1 X2]"""
import sys, re, os, shutil, bisect, json, collections
src, dst, NB, Y0, Y1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
X1 = float(sys.argv[6]) if len(sys.argv) > 6 else 552.0
X2 = float(sys.argv[7]) if len(sys.argv) > 7 else 200.0
shutil.copytree(src, dst)
W = json.load(open(src + "/probe.json"))["outline_um"][0]
TR = {"M4": (0.024, 0.048, "0.1920 0.0240"), "M6": (0.032, 0.064, "0.1920 0.0320")}
used = {(f, L): set() for f in "EW" for L in TR}
for ln in open(src + "/io.tcl"):
    m = re.search(r"-layer (M\d) -location \{([\d.]+) ([\d.]+)\}", ln)
    if not m or m[1] not in TR: continue
    x, y = float(m[2]), float(m[3])
    f = "W" if x < 1 else ("E" if x > W - 1 else None)
    if f:
        o, p, _ = TR[m[1]]
        used[(f, m[1])].add(round((y - o) / p))
def pick(f, L, y):
    o, p, _ = TR[L]
    k = round((y - o) / p)
    for d in range(0, 200):
        for kk in (k + d, k - d):
            if all(kk + e not in used[(f, L)] for e in (-1, 0, 1)):
                used[(f, L)].add(kk)
                return o + kk * p
    raise SystemExit(f"no track near {y} {f} {L}")
io, ports, cells, place = [], [], [], []
step = (Y1 - Y0) / NB
for b in range(NB):
    y = Y0 + (b + 0.5) * step
    L = "M4" if b % 2 else "M6"
    ye, yw = pick("E", L, y), pick("W", L, y)
    io.append(f"place_pin -pin_name {{VA_i[{b}]}} -layer {L} -location {{{W - 0.096:.4f} {ye:.4f}}} -pin_size {{{TR[L][2]}}}")
    io.append(f"place_pin -pin_name {{VA_o[{b}]}} -layer {L} -location {{0.0960 {yw:.4f}}} -pin_size {{{TR[L][2]}}}")
    cells.append(f"  DFFHQNx1_ASAP7_75t_R va_{b}_0 (.D(VA_i[{b}]), .QN(nva_{b}_0));")
    cells.append(f"  DFFHQNx1_ASAP7_75t_R va_{b}_1 (.D(nva_{b}_0), .QN(nva_{b}_1));")
    cells.append(f"  DFFHQNx1_ASAP7_75t_R va_{b}_2 (.D(nva_{b}_1), .QN(VA_o[{b}]));")
    place += [(f"va_{b}_0", W - 1.0 - 1.08, ye), (f"va_{b}_1", X1, y), (f"va_{b}_2", X2, yw)]
with open(dst + "/io.tcl", "a") as fh:
    fh.write("# DIE-HBM-36 V-A synthetic through bits\n" + "\n".join(io) + "\n")
v = open(src + "/probe.v").read()
hdr_end = v.index(");\n")
v = v[:hdr_end] + f",\n  input [{NB - 1}:0] VA_i,\n  output [{NB - 1}:0] VA_o" + v[hdr_end:]
wires = "\n".join(f"  wire nva_{b}_0;\n  wire nva_{b}_1;" for b in range(NB))
v = v.replace("endmodule", wires + "\n" + "\n".join(cells) + "\nendmodule")
open(dst + "/probe.v", "w").write(v)
t = open(src + "/probe.tcl").read()
pl = "\n".join(f"place_inst -name {c} -location {{{x:.3f} {y:.3f}}} -status PLACED" for c, x, y in place)
t = t.replace("detailed_placement -max_displacement", pl + "\ndetailed_placement -max_displacement", 1)
open(dst + "/probe.tcl", "w").write(t)
pj = json.load(open(src + "/probe.json")); pj.update(va_bits=NB, va_corridor=[Y0, Y1], va_x=[X1, X2],
    pins=pj["pins"] + 2 * NB, flops=pj["flops"] + 3 * NB, note="DIE-HBM-36 V-A 12/um probe")
json.dump(pj, open(dst + "/probe.json", "w"), indent=1)
rs = open(src + "/run.sh").read().replace(src, dst)
open(dst + "/run.sh", "w").write(rs)
print("added", NB, "bits", "corridor", Y0, Y1)
