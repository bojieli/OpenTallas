# calibrate die_trial leg_ps (STAGE_1X_TT, rep 250) against trial4 routed clock-only GRT arrivals, per corner
import json,math,statistics as st
R="/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028"
T=json.load(open(R+"/clockbuild/trial4_pad/clock/tree.json"));N=T["nodes"]
d0,k1,k2=(20.8281, 0.013984, 0.00033554)
def leg_ps(L,rep=250.0):
  n=max(1,int(math.ceil(L/rep-1e-9)));return n*d0+k1*L+k2*L*L/n
for c in ["TT","FF"]:
  nl={l.split()[1]:float(l.split()[2]) for l in open(R+f"/c1_{c}/arr_{c}.txt") if l.startswith("N ")}
  rat=[];rows=[]
  for i,n in N.items():
    p=n.get("parent")
    if p is None or ("b%s"%i) not in nl or ("b%s"%p) not in nl: continue
    P_=N[str(p)];L=abs(n["x"]-P_["x"])+abs(n["y"]-P_["y"])
    if L<100: continue
    m=nl["b%s"%i]-nl["b%s"%p];rat.append(m/leg_ps(L));rows.append((L,m))
  print(c,"legs",len(rat),"measured/model median",round(st.median(rat),3),"p10/p90",round(sorted(rat)[len(rat)//10],3),round(sorted(rat)[9*len(rat)//10],3))
