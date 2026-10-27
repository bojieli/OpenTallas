import json, sys
for d in sys.argv[1:]:
    for c in ("TT", "FF"):
        D = json.load(open(f"{d}/die_{c}.json"))
        s = D["summary"]
        sm = D["samples"]
        x, y = "sl_E0_hc0", "c_E0_tn_00"
        d0 = [q for q in sm if q["sample"] == 0][0]["tap_arr_ps"]
        dd = [round((q["tap_arr_ps"][x] - q["tap_arr_ps"][y]) - (d0[x] - d0[y]), 1) for q in sm if q["sample"] > 0]
        print(d.split("/")[-1], c, "nom skew", s["nominal_tap_skew_ps"], "MC worst", s["mc_worst_tap_skew_ps"], "mean", s["mc_mean_tap_skew_ps"],
              "ins", s["insertion_ps"], "worst-pair dd", dd)
