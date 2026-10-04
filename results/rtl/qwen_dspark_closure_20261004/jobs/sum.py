import json, glob, sys, os
for f in sorted(glob.glob(sys.argv[1] + "/*.json")):
    try: d = json.load(open(f))
    except Exception as e: print(f, "ERR", e); continue
    out = [os.path.basename(f)[:-5], "cells=%s" % d.get("synth", {}).get("cells")]
    for ph, pv in d.get("phases", {}).items():
        p = pv.get("r2r_path") or {}
        out.append("%s r2r=%.1f all=%.1f [%s -> %s]" % (ph, pv.get("r2r_setup_wns_ps") or 0, (pv.get("all_setup_wns_ps") or 0)*1, p.get("startpoint"), p.get("endpoint")))
        for fn, fv in (pv.get("focus") or {}).items():
            out.append("   %s.%s=%s n=%s" % (ph, fn, None if fv.get("setup_wns_ps") is None else round(fv["setup_wns_ps"], 1), fv.get("endpoints")))
    print("\n  ".join(out))
