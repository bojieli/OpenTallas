import json, sys, importlib.util
spec = importlib.util.spec_from_file_location("g", "in/gen_core_kit_hbm_rebal10.py"); g = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(g)
except SystemExit: pass
MG = json.load(open("in/macro_reg_guide_m5w1gr.json")); rel = json.load(open("in/relay_lanes_canon.json"))["relays"]
pins = json.load(open("../c24/cores/ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77__760.32x725.76__canon.json"))
P = [(r["name"], r["x"], r["y"]) for r in pins]
box = [4.32, 4.32, 756, 721.44]
base = g.relay_reg_guide_spec(rel, P, MG["guides"], box)
b3 = {r["name"]: r for r in base}["wvbank3"]; print("base", b3["point_um"], b3["hop_pins_um"], b3["hop_sinks_um"])
S = sorted(r["x"] for r in pins if r["y"] < 0.2 and r["name"] != "g_bank_k3_u_bank_write_v")
dmin = min(b - a for a, b in zip(S, S[1:])); print("S min spacing", dmin)
res = []
for k in range(int(4.32/0.048), int(756/0.048)):
    x = round(0.024 + k * 0.048, 3)
    if min(abs(x - s) for s in S) < dmin - 1e-9: continue
    if abs(x / 10 - round(x / 10)) * 10 > 0.03: continue
    P2 = [(n, x if n == "g_bank_k3_u_bank_write_v" else px, py) for n, px, py in P]
    r = {q["name"]: q for q in g.relay_reg_guide_spec(rel[-1:], P2, MG["guides"] + [dict(macro="~", box_um=q["box_um"]) for q in base if q["name"] != "wvbank3"], box)}["wvbank3"]
    res.append((max(r["hop_pins_um"], r["hop_sinks_um"]), x, r["point_um"], r["hop_pins_um"], r["hop_sinks_um"]))
res.sort(); print(res[:5]); json.dump(dict(base=b3, best=res[:5], spacing=dmin), open("wv3_probe.json","w"), indent=1)
