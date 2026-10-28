"""DIE-KV-2: measured count-aligned margins per region crossing.
ca_measured.py LPO_JSON REGIONS_JSON OUT_PREFIX
landed_phase_ocv rows (measured GRT-RC arrivals, shared derate) -> keep ports whose src/dst partitions are in DIFFERENT
regions (same-region pairs are related pairs for die STA), relabel src/dst = region, then count_align_plan.py (MESO-COUNT-1,
unchanged CLI: joint TT+FF union, ap = T/8).  Margins (COORD 20:35 (b)): lo = L_lo - 0.5T, hi = (DEPTH-0.5)T - L_hi."""
import json, sys, subprocess, collections
lpo, regf, pre = sys.argv[1:4]
reg = json.load(open(regf))["part_region"]
d = json.load(open(lpo))
keys = ["TT_droop-regions_corelat250", "FF_droop-regions_corelat202.5"]
for k in keys:
    rows = []
    for r in d["corners"][k]["all"]:
        a, b = reg[r["src"]], reg[r["dst"]]
        if a == b:
            continue
        rows.append(dict(r, src=a, dst=b, src_part=r["src"], dst_part=r["dst"]))
    d["corners"][k]["all"] = rows
json.dump(dict(corners={k: d["corners"][k] for k in keys}), open(pre + "_xing_lpo.json", "w"))
here = "/srv/opentallas-scratch2/claude/die-kv-2-1027/src/tools/die_plan/count_align_plan.py"
p = subprocess.run([sys.executable, here, pre + "_xing_lpo.json", "--corner", ",".join(keys), "--out", pre + "_ca.json"],
                   capture_output=True, text=True)
o = json.load(open(pre + "_ca.json"))
T = 833.0
W = {r["port"]: r.get("width", 1) for r in d["corners"][keys[0]]["all"]}
lo = [c["L_lo_ps"] - 0.5 * T for c in o["crossings"] if c["depth"]]
hi = [(c["depth"] - 0.5) * T - c["L_hi_ps"] for c in o["crossings"] if c["depth"]]
s = o["summary"]
res = dict(crossings=s["crossings"], regions=s["regions"], depth4=s["depth4"], depth8=s["depth8"], fail=s["fail"],
           tree_components=s["tree_components"], worst_lo=round(min(lo), 1) if lo else None,
           worst_hi=round(min(hi), 1) if hi else None, under100=sum(1 for a, b in zip(lo, hi) if min(a, b) < 100),
           max_path_amb=s["max_path_ambiguous_cycles"], max_L_width=s["max_L_width_ps"],
           tree_edges_ambiguous=len(s["tree_edges_ambiguous"]), rc=p.returncode,
           max_unshared_ps=max(max(r["unshared_a_ps"], r["unshared_b_ps"]) for r in d["corners"][keys[0]]["all"]))
json.dump(res, open(pre + "_ca_summary.json", "w"), indent=1)
print(json.dumps(res))
