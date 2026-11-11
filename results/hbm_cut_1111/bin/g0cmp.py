import json, sys
def load(p):
    r = json.load(open(p))
    return r
a, b = load(sys.argv[1]), load(sys.argv[2])
fa = {json.dumps(x, sort_keys=True) for x in a["findings"] if isinstance(x, dict) and x.get("severity", x.get("level", "")).lower().startswith("err")}
fb = {json.dumps(x, sort_keys=True) for x in b["findings"] if isinstance(x, dict) and x.get("severity", x.get("level", "")).lower().startswith("err")}
print(json.dumps({"base_errors": a["errors"], "new_errors": b["errors"], "base_warnings": a["warnings"], "new_warnings": b["warnings"],
                  "err_findings_base": len(fa), "err_findings_new": len(fb), "new_err": len(fb - fa), "lost_err": len(fa - fb)}))
for s in sorted(fb - fa)[:40]: print("+", s[:600])
for s in sorted(fa - fb)[:40]: print("-", s[:600])
