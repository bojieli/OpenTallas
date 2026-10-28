"""free intervals on the shared face a|b (core-clear CLEAR um each side, ports occupied) -- KV-PLAN-DELTA-8 diag"""
import sys, json
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]))
CLEAR=float(sys.argv[5]) if len(sys.argv)>5 else 20.0
a,b=sys.argv[3],sys.argv[4]
ax0,ay0,ax1,ay1=P.rect(a);bx0,by0,bx1,by1=P.rect(b)
if abs(ax1-bx0)<1e-3: face,lo,hi,line="E",max(ay0,by0),min(ay1,by1),ax1
elif abs(ax0-bx1)<1e-3: face,lo,hi,line="W",max(ay0,by0),min(ay1,by1),ax0
elif abs(ay1-by0)<1e-3: face,lo,hi,line="N",max(ax0,bx0),min(ax1,bx1),ay1
else: face,lo,hi,line="S",max(ax0,bx0),min(ax1,bx1),ay0
blk=[]
for part in (a,b):
    for bx in S.placed_macro_boxes(P.ptype(part)).values():
        p1=P.to_die(part,(bx[0],bx[1]));p2=P.to_die(part,(bx[2],bx[3]))
        x0,y0,x1,y1=min(p1[0],p2[0]),min(p1[1],p2[1]),max(p1[0],p2[0]),max(p1[1],p2[1])
        if face in "EW":
            if x1>line-CLEAR and x0<line+CLEAR: blk.append((y0,y1,"core"))
        elif y1>line-CLEAR and y0<line+CLEAR: blk.append((x0,x1,"core"))
for pid,pr in P.ports.items():
    if {pr["src"]["part"],pr["dst"]["part"]}=={a,b}:
        cs=[c for _,_,c in P.port_pins(pid)]; blk.append((min(cs),max(cs),pid+":%d"%len(cs)))
blk.sort()
print(face,"face",round(lo,2),round(hi,2),"len",round(hi-lo,1))
for x in blk: print("  blk",round(x[0],1),round(x[1],1),x[2])
cur=lo;free=[]
for s,e,_ in blk:
    if s>cur: free.append((cur,s))
    cur=max(cur,e)
if hi>cur: free.append((cur,hi))
print("free",[(round(s,1),round(e,1),round(e-s,1)) for s,e in free if e-s>5])
