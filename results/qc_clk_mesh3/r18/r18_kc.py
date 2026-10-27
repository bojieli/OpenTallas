import json, sys
d = json.load(open(sys.argv[1]))
for c in ("TT", "FF"):
    s = d["corners"][c]["classes"]["seam"]
    for k in ("kit_contract_hold", "kit_contract_hold_cv", "zero_logic"):
        if k in s:
            print(c, k, json.dumps(s[k])[:1500])
    print(c, "keys", list(s.keys()))
