import json,sys,collections
P={(o["C"],o["port"]):o for o in json.load(open("/srv/opentallas-scratch2/claude/die-head-19/ports_r1.json"))}
for n in sys.argv[1:]:
    s=json.load(open(f"/srv/opentallas-scratch2/claude/die-head-19/whatif/{n}/sta/die_sta_related.json"))
    for C in ("TT","FF"):
        c=collections.Counter()
        for r in s["count_aligned"][C]["rows"]:
            if not (r["lag_ok"] and r["guard_ok"]): o=P[(C,r["port"])]; c[(o["ts"],o["td"])]+=1
        print(n,C,dict(c))
