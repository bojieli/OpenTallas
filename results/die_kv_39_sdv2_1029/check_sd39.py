"""DIE-KV-39 V2: evaluate the sd39 plan delta with the existing plan tools (no new check): explicit tap loads/radius,
reset_tree.for_type relays vs the PHY footprint.  usage: check_sd39.py TOOLS PLAN"""
import sys, json
sys.path.insert(0, sys.argv[1])
import schema as S, taps as T, reset_tree as RT
P = S.Plan(S.load(sys.argv[2]), sys.argv[2])
out = {}
for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
    r = dict(macro=S.placed_macro_boxes(P.types[tn]))
    try:
        r["taps"] = [dict(name=n, xy=[x, y], load=l, far_um=round(f, 1)) for n, x, y, l, f in T.explicit_taps(P, tn)]
    except Exception as e:
        r["taps_error"] = str(e)
    try:
        t = RT.for_type(P, tn)
        mb = S.placed_macro_boxes(P.types[tn], halo=4.32).values()
        on = [x["q"] for x in t["relays"] if any(a < x["xy"][0] < c and b < x["xy"][1] < d for a, b, c, d in mb)]
        r["reset"] = dict(depth=t.get("depth"), relays=len(t["relays"]), max_hop_um=t.get("max_hop_um"), taps=t.get("taps"),
                          relays_on_macro=on)
    except Exception as e:
        r["reset_error"] = repr(e)
    out[tn] = r
print(json.dumps(out, indent=1, default=str))
