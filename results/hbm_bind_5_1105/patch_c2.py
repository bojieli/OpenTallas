#!/usr/bin/env python3
"""Join the spliced FUSED lanes to the top pair cells hb_fvp_S*k: lane rq/wq outputs into the pair inputs, pair rr outputs into lane rr inputs. usage: patch_c2.py IN OUT RECEIPT"""
import json, sys
J = json.load(open(sys.argv[1])); M = J["modules"]["hbm_current_native_top"]; C = M["cells"]
done = []; sub = {}; dead = set()
for side, role in (("nw", "SW"), ("ne", "SE")):
    for k in range(8):
        pr = C[f"hb_fvp_{role}{k}"]["connections"]
        for t, L in (("a", 2 * k), ("b", 2 * k + 1)):
            lc = C[f"u_mu_fused_{L}_{side}"]["connections"]
            for lp in ("rq_v", "rq_s", "wq_v", "wq_s", "wq_d"):
                pp = f"{t}_{lp}"; old = pr[pp]; assert len(old) == len(lc[lp]), (pp, lp)
                for o, n in zip(old, lc[lp]): sub[o] = n
            for lp, pp in (("rr_v", f"{t}_rr_v"), ("rr_d", f"{t}_rr_d")):
                old = lc[lp]; assert len(old) == len(pr[pp]), lp
                for o in old: dead.add(o)
                lc[lp] = list(pr[pp])
            done.append((L, side, role, k))
for name, c in C.items():
    for p, bits in c["connections"].items():
        c["connections"][p] = [sub.get(b, b) for b in bits]
rm = []
for n, p in list(M["ports"].items()):
    if n.startswith("fvp_in__") or (n.startswith("native_required__u_mu_fused_") and n.endswith(("__rr_v", "__rr_d"))):
        rm.append(n); del M["ports"][n]; M["netnames"].pop(n, None)
json.dump(J, open(sys.argv[2], "w")); json.dump(dict(joined=len(done), ports_removed=len(rm)), open(sys.argv[3], "w"))
print("C2 joined", len(done), "ports removed", len(rm))
