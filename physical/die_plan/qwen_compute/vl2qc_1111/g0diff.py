import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
fa = {(f["level"], f["check"], f["msg"]) for f in a["findings"]}
fb = {(f["level"], f["check"], f["msg"]) for f in b["findings"]}
print("base", a["errors"], a["warnings"], "cand", b["errors"], b["warnings"])
for x in sorted(fb - fa): print("NEW", x[0], x[1], x[2][:300])
for x in sorted(fa - fb): print("GONE", x[0], x[1], x[2][:300])
