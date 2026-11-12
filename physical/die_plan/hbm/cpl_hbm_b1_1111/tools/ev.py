"""fast loop for one type: candidate type json -> mini plan -> route_supply (maps) p99 + hot clusters, and the cut
blocked-length budget (union of core intervals on every 250-um die line through each partition of the type vs
blk_max from the t19 budget). usage: ev.py TYPE CAND_TYPE.json [THR]"""
import json, sys, subprocess, os
B = "/srv/opentallas-scratch3/claude/cpl-hbm-b1/lad"
tn, cf = sys.argv[1], sys.argv[2]; thr = sys.argv[3] if len(sys.argv) > 3 else "2.0"
T = json.load(open(cf))
P = json.load(open(f"{B}/mini/die_plan.json")); P["partition_types"][tn] = T
os.makedirs(f"{B}/minix", exist_ok=True)
for f in os.listdir(f"{B}/mini"):
    if f != "die_plan.json" and not os.path.exists(f"{B}/minix/{f}"): os.symlink(os.path.realpath(f"{B}/mini/{f}"), f"{B}/minix/{f}")
json.dump(P, open(f"{B}/minix/die_plan.json", "w"))
# cut budget
bud = {}
for line in open(f"{B}/budget_t19.txt"):
    f = line.split("\t"); part, t, oc = f[0], f[1].strip(), f[2]
    bud[(part, oc)] = float(f[7].split()[1])
W, H = T["outline_um"]; bad = []
for p in P["partitions"]:
    if p["type"] != tn: continue
    ox, oy = p["origin_um"]; o = p.get("orient", "R0")
    for orient, lo, hi in (("h", oy, oy + H), ("v", ox, ox + W)):
        k = int(lo // 250) + 1
        while k * 250 < hi:
            c = k * 250; cl = c - (oy if orient == "h" else ox)
            if orient == "v" and o in ("MY", "R180"): cl = W - cl
            if orient == "h" and o in ("MX", "R180"): cl = H - cl
            iv = []
            for h in T["hard_cores"]:
                (x, y), (w, hh) = h["origin_um"], h["outline_um"]
                if orient == "h" and y + 1e-6 < cl < y + hh - 1e-6: iv.append((x, x + w))
                if orient == "v" and x + 1e-6 < cl < x + w - 1e-6: iv.append((y, y + hh))
            iv.sort(); tot = 0; cur = None
            for a, b in iv:
                if cur and a <= cur[1]: cur[1] = max(cur[1], b)
                else:
                    if cur: tot += cur[1] - cur[0]
                    cur = [a, b]
            if cur: tot += cur[1] - cur[0]
            m = bud.get((p["name"], f"{orient}{c}"))
            if m is not None and tot > m + 1: bad.append((p["name"], f"{orient}{c}", round(cl, 1), round(tot), round(m)))
            k += 1
print("CUT", "OK" if not bad else bad)
r = subprocess.run(["nice", "-n", "19", "python3", "-I", "tools/die_plan/route_supply.py", f"{B}/minix/die_plan.json", "--die", "hbm", "--repo", ".",
                    "--ref-dirs", f"{B}/minix", "--types", tn, "--maps", "--out", f"{B}/minix.rs"], cwd=f"{B}/wt", capture_output=True, text=True)
for l in open(f"{B}/minix.rs/route_supply_hbm.tsv"):
    f = l.split("\t")
    if f[1] == tn: print("RS", tn, "p99", f[7], "worst", f[4], f[5], f[10], "|", f[3])
print(subprocess.run(["python3", "-I", f"{B}/hotcl.py", f"{B}/minix.rs/hbm__{tn}.npz", thr], capture_output=True, text=True).stdout)
