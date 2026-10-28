# WHAT-IF (diagnostic, not a gate input): clock early arrival = late arrival (one RC/cap value per net), so the
# late/early split on unshared branches comes only from the AOCV table (Ainv MC rows), not from the Liberty
# rise/fall_capacitance_range (CKINVDCx16 A 6.68..9.54 fF) that OpenSTA applies as min cap on the early path.
import json,sys
src,dst=sys.argv[1],sys.argv[2]
for C in ("TT","FF"):
    d=json.load(open(f"{src}/tap_arrivals_{C}.json"))
    for t in d["taps"]:
        for a,b in (("early_ps","late_ps"),("abs_early_ps","abs_late_ps")):
            if b in t: t[a]=t[b]
    d["node_early_ps"]={k:d["node_late_ps"][k] for k in d["node_early_ps"]}
    d["whatif"]="early:=late on the clock network (nominal cap); DIE-S81-14 diagnostic"
    json.dump(d,open(f"{dst}/tap_arrivals_{C}.json","w"))
print("ok")
