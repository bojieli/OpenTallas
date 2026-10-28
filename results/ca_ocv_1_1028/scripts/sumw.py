import json,sys
d=json.load(open(sys.argv[1]))
for c in ("TT","FF"):
    w=d["corners"][c]["with_ocv"]; n=d["corners"][c]["no_ocv"]
    print(c, "cross",w["crossings"],"sta",w["sta_timed"],"<100",w["below_need"],"lo",w["worst_lo"],w["worst_lo_port"],"hi",w["worst_hi"],w["worst_hi_port"],"ocvmax",w["ocv_max_lo"],w["ocv_max_hi"],"slot",w["slot_read_fail"],"guard",w["guard_fail"],"start",w["start_skew_fail"],"| base lo/hi",n["worst_lo"],n["worst_hi"],"start",n["start_skew_fail"], "neg", sum(1 for r in w["worst10"] if min(r["margin_lo_ps"],r["margin_hi_ps"])<0))
