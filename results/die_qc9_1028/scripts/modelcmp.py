import json,sys,math
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude/die-qc9-1028")
T=json.load(open(Q/"trial7/clock/tree.json"));N=T["nodes"]
def leg_ps(L,rep=250):
  n=max(1,math.ceil(L/rep-1e-9));return n*20.8281+0.013984*L+0.00033554*L*L/n
arr={};narr={}
for l in open(Q/"c7_TT/arr_TT.txt"):
  f=l.split()
  if f[0]=="T": arr[f[1]]=float(f[2])
  if f[0]=="N": narr[f[1]]=float(f[2])
g=sys.argv[1]
ent=[i for i,n in N.items() if n.get("dme")==g and str(n["parent"]) in N and N[str(n["parent"])].get("dme")!=g][0]
pe=str(N[ent]["parent"])
def walk(i,a,path):
  n=N[i];p=N[str(n["parent"])]
  L=abs(n["x"]-p["x"])+abs(n["y"]-p["y"])+n.get("detour_um",0)
  a+=leg_ps(L);path=path+[(i,round(L))]
  for t in T["taps"]:
    if str(t["node"])==i:
      d=abs(t["xy"][0]-n["x"])+abs(t["xy"][1]-n["y"])
      m=arr[t["port"]]-narr["b"+pe]
      print(f'{t["port"]:32s} model {a:7.1f} meas {m:7.1f} ratio {m/a:5.2f} depth {len(path)} legs {[l for _,l in path]}')
  for k in n["kids"]: walk(str(k),a,path)
walk(ent,0.0,[])
