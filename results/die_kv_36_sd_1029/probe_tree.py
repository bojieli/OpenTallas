import json, sys, time
sys.path.insert(0, sys.argv[1])
import schema as S, reset_tree as RT
for pl in sys.argv[2:]:
    t0 = time.time()
    P = S.Plan(json.load(open(pl)), pl)
    for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
        T = RT.for_type(P, tn)
        taps = [(r["q"], r["xy"]) for r in T["relays"] if r["q"].startswith("rst_n_t")]
        ox, oy, w, h = 17.28, 54.0, 1848.96, 972.0
        on = [r["name"] for r in T["relays"] if ox - 4.32 < r["xy"][0] < ox + w + 4.32 and oy - 4.32 < r["xy"][1] < oy + h + 4.32]
        print(pl.split('/')[-1], tn, "relays", len(T["relays"]), "depth", T["depth"], "maxhop", T["max_hop_um"], "taps", len(taps), "on_macro", on, "entry", T.get("entry"), round(time.time() - t0, 1), "s")
        print("  ", sorted(taps, key=lambda x: int(x[0][7:])))
