import json,sys,collections
sys.path.insert(0,"/srv/opentallas-scratch2/claude/hbm-bind-5/tools/die_plan")
import schema as S
def pairs(f):
    raw=json.load(open(f)); P=S.Plan(raw); L=raw["latency"]["lanes"]; out=collections.defaultdict(list)
    for lid in P.lanes:
        hp=[P.ports[q] for q in P.lanes[lid]["ports"]]; a=hp[0]["src"]["part"]; z=hp[-1]["dst"]["part"]
        c=L.get(lid,{}).get("cycles")
        if c is None: c=P.lane_natural(lid)["cycles"]
        out[(a,z)].append((int(c),hp[0]["width"],lid))
    return out
p7=pairs(sys.argv[1]); k=pairs(sys.argv[2])
rows=[]
for pr in sorted(set(p7)|set(k)):
    a=p7.get(pr,[]); b=k.get(pr,[])
    ma=max([x[0] for x in a] or [None]) if a else None; mb=max([x[0] for x in b]) if b else None
    if ma!=mb: rows.append((pr,ma,mb,sum(x[1] for x in a),sum(x[1] for x in b)))
for r in rows: print(f"{r[0][0]}->{r[0][1]}\tp7max {r[1]}\tCmax {r[2]}\tbits {r[3]}/{r[4]}")
print("pairs changed",len(rows))
