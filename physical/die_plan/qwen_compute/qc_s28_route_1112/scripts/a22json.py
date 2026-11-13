import json, sys
out = {}
for tn, base in (("cbx_q10__cl89936551", 0.0), ("cbx_q10__cl94a12200", 0.0), ("cbx_q10__cl89936551_h", 34.56), ("cbx_q10__cl94a12200_h", 34.56)):
    out[tn] = dict(in_window_um=[round(2438.112 + base, 4), round(2527.2 + base, 4)], in_layers=["M6", "M4"], in_order="lsb_high")
json.dump(out, open(sys.argv[1], "w"), indent=1)
