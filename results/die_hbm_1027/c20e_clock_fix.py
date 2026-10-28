"""DIE-HBM-2 C20e = C20d + (a) u_tkmclk_L150_c0 branch buffer re-sited into the tile6/tile7 corridor gap column
(the C20b re-pack moved tile6 under it; legs 371.52/371.52 um) + (b) tkm leg repeaters that ft_nudge bit sites now
crowd (2-um station halo) slide along x on their own row to the nearest clear point (off every core).
usage: c20e_clock_fix.py REPO PLAN_DIR(in place)"""
import json, hashlib, sys
REPO, D = sys.argv[1:3]
sys.path.insert(0, REPO + "/tools/die_plan")
import check as C
p = D + "/die_plan.json"; raw = json.load(open(p)); t = raw["partition_types"]["root"]; ck = t["clock"]
taps = {x["name"]: x["xy"] for x in ck["taps"]}
boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"]]
rep = []
b = next(x for x in ck["branch_buffers"] if x["name"] == "u_tkmclk_L150_c0")
if b["xy"] != [509.76, 4190.4]:
    rep.append(("u_tkmclk_L150_c0", b["xy"], [509.76, 4190.4]))
    b["xy"] = [509.76, 4190.4]; b["cell_ll_um"] = [round(509.76 - 0.702, 4), round(4190.4 - 0.135, 4)]
    b["legs_um"] = [round(abs(taps[d][0] - 509.76) + abs(taps[d][1] - 4190.4), 3) for d in b["drives"]]
for b in ck["branch_buffers"]:
    if "tkmclk" not in b["name"]: continue
    for r in b.get("leg_repeaters") or []:
        if not C._buf_near_station(t, r["xy"]): continue
        x0, y = r["xy"]; found = None
        for k in range(1, 80):
            for s in (1, -1):
                q = [round(x0 + s * 0.216 * k, 4), y]; ll = [round(q[0] - 0.702, 4), r["cell_ll_um"][1]]
                if any(ll[0] < e and ll[0] + 1.404 > a and ll[1] < f and ll[1] + 0.27 > c for a, c, e, f in boxes): continue
                if C._buf_near_station(t, q): continue
                found = (q, ll); break
            if found: break
        rep.append((r["name"], r["xy"], found and found[0]))
        if found: r["xy"], r["cell_ll_um"] = found
raw["die"]["label"] = "C20e = C20d + tkm clock buffer/repeater re-site | " + raw["die"]["label"].split(" | ", 1)[-1]
open(p, "w").write(json.dumps(raw, indent=1))
open(D + "/die_plan.sha256", "w").write(hashlib.sha256(open(p, "rb").read()).hexdigest() + "\n")
json.dump(rep, open(D + "/c20e_clock_fix_report.json", "w"), indent=1); print(rep)
