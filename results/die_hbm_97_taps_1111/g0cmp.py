import json, sys, collections
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
def errs(g):
    return collections.Counter(json.dumps({k: f.get(k) for k in ("rule", "check", "type", "partition", "msg", "message") if k in f}, sort_keys=True)
                               for f in g["findings"] if f.get("severity", f.get("level")) in ("ERROR", "error", "FAIL"))
ea, eb = errs(a), errs(b)
new = eb - ea; gone = ea - eb
print("base errors", a["errors"], "new errors", b["errors"], "warnings", a["warnings"], b["warnings"])
print("new error findings", sum(new.values())); [print("  +", k[:300]) for k in list(new)[:15]]
print("gone error findings", sum(gone.values())); [print("  -", k[:300]) for k in list(gone)[:8]]
json.dump(dict(base_errors=a["errors"], new_errors=b["errors"], base_warnings=a["warnings"], new_warnings=b["warnings"],
               new_findings=list(new), gone_findings=list(gone)), open(sys.argv[3], "w"), indent=1)
