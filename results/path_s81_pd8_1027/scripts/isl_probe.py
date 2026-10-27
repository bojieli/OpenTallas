"""PATH-S81-PD8 GRT PROBE ONLY: declare the 3 residual bk_sel pushdown cells (md3) as island windows so combo can
generate the die GRT deck. NOT a legal plan: dsdv_bksel_q island identity FAILS (2 of 4 instances); see lane line."""
import json, sys
sys.path.insert(0, sys.argv[3])
import die_clock_mesh as D
src, dst = sys.argv[1], sys.argv[2]
M = json.load(open(src + "/mesh.json"))
P = json.load(open(src + "/place.json"))
names = set()
for r in M["pushdown"]:
    if r["role"] == "mesh_driver":
        names |= set(M["drivers"][r["name"].replace("ckm_d_", "")]["cells"])
    else:
        names.add(r["name"])
W = M.setdefault("island_windows", [])
for n in sorted(names):
    c = P[n]
    W.append([round(c["x"] - D.SITE_X, 4), round(c["y"] - 1e-3, 4), round(c["x"] + D.BUF_W + D.SITE_X, 4),
              round(c["y"] + D.ROW_Y + 1e-3, 4), "PROBE_ONLY_bk_sel"])
M["meta"]["probe_islands"] = sorted(names)
json.dump(M, open(dst + "/mesh.json", "w"), indent=1)
print("island windows", len(W), sorted(names))
