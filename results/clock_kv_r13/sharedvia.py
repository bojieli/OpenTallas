import json,sys,collections
m=json.load(open(sys.argv[1]))
n=0; nets=0; lv=collections.Counter()
for w in m["fixed_wires"]:
    segs=w["segs"]
    if not segs: continue
    t=segs[0]
    cnt=0
    if w["horiz"]:
        ty=t[2]; d=[(s[1],s[2],s[4]) for s in segs[1:] if s[0]=="M9"]
        for i in range(len(d)):
            for j in range(i+1,len(d)):
                if abs(d[i][0]-d[j][0])<1e-6 and (min(d[i][1],d[i][2])<ty-1e-6)!=(min(d[j][1],d[j][2])<ty-1e-6): cnt+=1
    else:
        tx=t[1]; d=[(s[2],s[1],s[3]) for s in segs[1:] if s[0]=="M8"]
        for i in range(len(d)):
            for j in range(i+1,len(d)):
                if abs(d[i][0]-d[j][0])<1e-6 and (min(d[i][1],d[i][2])<tx-1e-6)!=(min(d[j][1],d[j][2])<tx-1e-6): cnt+=1
    if cnt: nets+=1; n+=cnt; lv[w["name"][:8]]+=1
print("shared-junction drop pairs",n,"nets",nets, dict(lv.most_common(5)))
