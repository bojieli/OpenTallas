#!/usr/bin/env python3
"""List die/item with an OT_CLAND no-legal-site failure in the wave attempt results of the last H hours. Output: die<TAB>item<TAB>last_t<TAB>attempt."""
import json, sys, time, glob, os
H = float(sys.argv[1]) if len(sys.argv) > 1 else 48
root = os.path.expanduser("~/coord/autopilot/kit_wave")
now = time.time(); best = {}; later_pass = {}
for rj in glob.glob(root + "/*/a*/result.json"):
    try:
        if now - os.path.getmtime(rj) > H * 3600: continue
        txt = open(rj, errors="replace").read()
    except OSError: continue
    try:
        dd = json.loads(txt)
        if dd.get("verdict") in ("PASS", "OK") and dd.get("stage") in ("place", "route", "signoff", "gen_kit", "flow", "done"):
            later_pass[(dd.get("die"), dd.get("item"))] = max(os.path.getmtime(rj), later_pass.get((dd.get("die"), dd.get("item")), 0))
    except ValueError: pass
    if "OT_CLAND" not in txt and "clock-landing band too small" not in txt: continue
    try: d = json.loads(txt)
    except ValueError: continue
    if d.get("verdict") not in ("FAIL", "ERROR", None): continue
    blob = json.dumps(d)
    if "no legal nonoverlapping" not in blob and "OT_CLAND" not in blob and "clock-landing band" not in blob: continue
    k = (d.get("die"), d.get("item")); t = os.path.getmtime(rj)
    if k not in best or t > best[k][0]: best[k] = (t, rj.split("/")[-2])
for (die, item), (t, a) in sorted(best.items(), key=lambda x: str(x[0])):
    if later_pass.get((die, item), 0) > t: continue
    print("%s\t%s\t%s\t%s" % (die, item, time.strftime("%m-%d %H:%M", time.localtime(t)), a))
