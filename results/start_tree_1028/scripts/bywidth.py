import json,sys
for f in sys.argv[1:]:
    d=json.load(open(f)); T=d["summary"]["period_ps"]; ap=d["summary"]["aperture_ps"]
    w=[e["p_up_ps"]+e["p_dn_ps"] for e in d["start_edges"]]
    nb=sum(1 for x in w if x>T/2-2*ap)
    print(f, "ports",len(w),"clean-by-phase (width >",round(T/2-2*ap),")",nb, f"{100*nb/len(w):.0f}%")
