import json,glob,os
for d in ("nl","nk","nl2"):
    for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__),d,"ocv_b*.json")),key=lambda s:int(s.rsplit("_b",1)[1][:-5])):
        o=json.load(open(f)); print(d, os.path.basename(f)[4:-5], "TT nom %.1f ocv %.1f | FF nom %.1f ocv %.1f"%(o["TT"]["nominal_spread"],o["TT"]["ocv_inclusive_spread"],o["FF"]["nominal_spread"],o["FF"]["ocv_inclusive_spread"]))
