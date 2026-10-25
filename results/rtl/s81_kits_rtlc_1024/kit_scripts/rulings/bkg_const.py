import json, sys
L = sys.argv[1] + "/physical/die_plan/s81/inputs/const_pins_dropped.json"
d = json.load(open(L)); e = d["modules"]["dsdv_bk_g"]
add = ["tap_k[1]", "tap_k[2]", "sink_k[1]", "sink_k[2]"]
assert not set(add) & set(e["pins"])
e["pins"] = e["pins"] + add
for b in ("tap_k", "sink_k"):
    for i in range(3, 8):
        e["rename"]["%s[%d]" % (b, i)] = "%s[%d]" % (b, i - 2)
e["why"] += ("; S81-KITS-RTLC 10-25: tap_k / sink_k bits 1 / 2 (kinds K_XQ / K_XB) are never read by ot_dsdv_vstop "
             "(those kinds are excluded from tap / sink): dropped, straps packed to [5:0] = {k[7:3], k[0]} at every "
             "dsdv_bk_g instance (renamed k[3..7] -> k[1..5])")
json.dump(d, open(L, "w"), indent=1); print("ok", len(e["pins"]), len(e["rename"]))
