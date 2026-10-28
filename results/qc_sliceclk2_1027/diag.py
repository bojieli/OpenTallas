import json,sys,collections
d="/srv/opentallas-scratch2/claude/qc-sliceclk-1027/"
t=json.load(open(d+"trial/clock/tree.json"));R=json.load(open(d+"fs/regions.json"))
po=t["parent_of"];S=t["sites"];N=t["nodes"]
arr={l.split()[1]:float(l.split()[2]) for l in open(d+"trial/clock/arr_TT.txt") if l.startswith("T ")}
narr={l.split()[1]:float(l.split()[2]) for l in open(d+"trial/clock/arr_TT.txt") if l.startswith("N ")}
print("node arr lines",len(narr))
reg=R["part_region"]
rows=[]
for tp in t["taps"]:
    if reg.get(tp["part"])!="E2": continue
    k=t["node_buf"][str(tp["node"])];x0,y0=tp["xy"];x1,y1=S[k];L=abs(x1-x0)+abs(y1-y0);n=1;x0,y0=x1,y1
    # stop at region root node
    nd=N[str(tp["node"])];
    while True:
        if k not in po: break
        q=po[k];x1,y1=S[q];L+=abs(x1-x0)+abs(y1-y0);x0,y0=x1,y1;k=q;n+=1
    lev=nd["level"]; ntap=sum(1 for _ in nd.get("taps",[]))
    rows.append((arr[tp["port"]],L/1000,n,lev,tp["xy"][1]/1000,len(nd.get("taps",[])),tp["port"]))
rows.sort()
for r in rows[:5]+rows[len(rows)//2:len(rows)//2+3]+rows[-5:]: print(["%.2f"%v if isinstance(v,float) else v for v in r])
print(len(rows))
