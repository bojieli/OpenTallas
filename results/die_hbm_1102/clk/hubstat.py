import json,sys
for d in sys.argv[1:]:
  for c in ("TT","FF"):
    p=json.load(open(d+"/proof/tap_arrivals_%s.json"%c))
    for part in ("NW_hub","NE_hub"):
      t=[x for x in p["taps"] if x["part"]==part]; L=[x["late_ps"] for x in t]
      print(d,c,part,"taps",len(t),"late min %.1f max %.1f spread %.1f"%(min(L),max(L),max(L)-min(L)))
