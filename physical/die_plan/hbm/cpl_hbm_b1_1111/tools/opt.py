"""CPL-HBM-B1 street-widening search for one type: first-improvement coordinate descent over the spec positions of
idx frames (units) and banks; every candidate = lad.py (positions + register re-site) -> legality / h0h1 / ft+st fail
/ reach no worse than base -> cut blocked-length budget vs t19 -> route_supply p99 (maps off). usage: opt.py TYPE PASSES"""
import json, sys, subprocess, os, copy, re
B = "/srv/opentallas-scratch3/claude/cpl-hbm-b1/lad"
tn = sys.argv[1]; passes = int(sys.argv[2]); W_ = f"{B}/opt/{tn}"; os.makedirs(W_, exist_ok=True)
SPEC = json.load(open(f"{B}/spec.json"))
base_t = json.load(open(f"{B}/out_c4/{tn}.json"))
sp = copy.deepcopy(SPEC[tn]); sp.setdefault("banks", {})
for h in base_t["hard_cores"]:
    m = re.search(r"bank128_(pair\d+)$", h["inst"])
    if m and m.group(1) not in sp["banks"]: sp["banks"][m.group(1)] = list(h["origin_um"])
P0 = json.load(open(f"{B}/mini/die_plan.json"))
mdir = f"{W_}/mini"; os.makedirs(mdir, exist_ok=True)
for f in os.listdir(f"{B}/mini"):
    if f != "die_plan.json" and not os.path.exists(f"{mdir}/{f}"): os.symlink(os.path.realpath(f"{B}/mini/{f}"), f"{mdir}/{f}")
bud = {}
for line in open(f"{B}/budget_t19.txt"):
    f = line.split("\t"); bud[(f[0], f[2])] = float(f[7].split()[1])
def cut_ok(T):
    W, H = T["outline_um"]
    for p in P0["partitions"]:
        if p["type"] != tn: continue
        ox, oy = p["origin_um"]; o = p.get("orient", "R0")
        for orient, lo, hi in (("h", oy, oy + H), ("v", ox, ox + W)):
            k = int(lo // 250) + 1
            while k * 250 < hi:
                c = k * 250; cl = c - (oy if orient == "h" else ox)
                if orient == "v" and o in ("MY", "R180"): cl = W - cl
                if orient == "h" and o in ("MX", "R180"): cl = H - cl
                iv = sorted((x, x + w) if orient == "h" else (y, y + hh) for h in T["hard_cores"] for (x, y), (w, hh) in [(h["origin_um"], h["outline_um"])]
                            if (orient == "h" and y + 1e-6 < cl < y + hh - 1e-6) or (orient == "v" and x + 1e-6 < cl < x + w - 1e-6))
                tot = 0; cur = None
                for a, b in iv:
                    if cur and a <= cur[1]: cur[1] = max(cur[1], b)
                    else:
                        if cur: tot += cur[1] - cur[0]
                        cur = [a, b]
                if cur: tot += cur[1] - cur[0]
                m = bud.get((p["name"], f"{orient}{c}"))
                if m is not None and tot > m + 1: return False
                k += 1
    return True
def rkey(r): return {(a, b): d for a, b, n, d in r}
def evaluate(s, tag):
    S2 = dict(SPEC); S2[tn] = s; json.dump(S2, open(f"{W_}/spec.json", "w"))
    r = subprocess.run(["python3", "-I", "lad.py", "t19/die_plan.json", tn, f"{W_}/spec.json", f"{W_}/c.json", f"../tr/{tn.replace('__physical_v1', '')}.json"],
                       cwd=B, capture_output=True, text=True)
    js = [l for l in r.stdout.splitlines() if l.startswith("{")]
    if r.returncode or not js: return None, "lad"
    d = json.loads(js[-1])
    if d["illegal"] or set(d["unplaced"]) - set(d0["unplaced"]) or d["h0h1_over405"] or d["ft_fail"] or d["st_fail"]: return None, "legal"
    rv = rkey(d["reach_viol"])
    if any(k not in RV0 or v > RV0[k] + 0.5 for k, v in rv.items()): return None, "reach"
    T = json.load(open(f"{W_}/c.json"))
    if not cut_ok(T): return None, "cut"
    P = dict(P0); P["partition_types"] = dict(P0["partition_types"]); P["partition_types"][tn] = T
    json.dump(P, open(f"{mdir}/die_plan.json", "w"))
    r = subprocess.run(["python3", "-I", "tools/die_plan/route_supply.py", f"{mdir}/die_plan.json", "--die", "hbm", "--repo", ".", "--ref-dirs", mdir,
                        "--types", tn, "--out", f"{W_}/rs"], cwd=f"{B}/wt", capture_output=True, text=True)
    for l in open(f"{W_}/rs/route_supply_hbm.tsv"):
        f = l.split("\t")
        if f[1] == tn: return float(f[7]), f[3]
    return None, "rs"
d0 = json.loads([l for l in open(f"{B}/out_c4/{tn}.log") if l.startswith("{")][-1]); RV0 = rkey(d0["reach_viol"])
best, why = evaluate(sp, "base"); print("BASE", best, why, flush=True)
keys = [("units", k) for k in sp.get("units", {})] + [("rows", i) for i in range(len(sp.get("rows", [])))] + [("banks", k) for k in sp["banks"]]
steps = [43.2, 21.6, 10.8, 4.32, 1.728, 0.864]
for ps in range(passes):
    imp = False
    for grp, k in keys:
        for st in steps:
            for ax in (0, 1):
                for sg in (1, -1):
                    c = copy.deepcopy(sp); e = c[grp][k]
                    if grp == "units": e[1 + ax] = round(e[1 + ax] + sg * st, 3)
                    elif grp == "rows":
                        if ax: e["y"] = round(e["y"] + sg * st, 3)
                        else: e["x0"] = round(e["x0"] + sg * st, 3); e["x1"] = round(e["x1"] + sg * st, 3)
                    else: e[ax] = round(e[ax] + sg * st, 3)
                    v, w = evaluate(c, k)
                    if v is not None and v < best - 1e-3:
                        best, sp, imp = v, c, True
                        print(f"pass{ps} {grp}:{k} ax{ax} {sg * st:+} -> {v} | {w}", flush=True)
                        json.dump(sp, open(f"{W_}/best_spec.json", "w"), indent=1)
    if not imp: break
json.dump(sp, open(f"{W_}/best_spec.json", "w"), indent=1); print("DONE", best, flush=True)
