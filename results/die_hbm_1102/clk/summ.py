import json,sys
for d in sys.argv[1:]:
    t=open(d+"/sta.log").read(); j=json.loads(t[t.rindex("SUMMARY ")+8:].splitlines()[0])
    g=j["die_clock_gate"]; print(d, {k:g.get(k) for k in ("tt_setup_ps","ff_hold_ps","contract_violations","verdict","reasons","skew_max_ps")}, "landed",j["landed"]["verdict"], j["landed"]["worst_margin_lo_ps"])
    for p in ("intra","seam"): print("  ",p,j[p]["kit_contract_window_needed_ps"],j[p]["kit_contract_verdict"],j[p]["hb4"]["pairs_needing_hb"])
