# c_* root cause check: path wire excess from site slides (placed vs req) vs measured tree arrival inside the region
import json,collections,statistics as st
R="/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028"
T=json.load(open(R+"/clockbuild/trial4_pad/clock/tree.json"));N=T["nodes"]
D=json.load(open("/tmp/qc8_est_rows.json"))["TT"]["rows"]
reg=json.load(open(R+"/build_inputs/part_region.json"))["part_region"]
def man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
G=collections.defaultdict(list)
for t in T["taps"]:
  if not t["part"].startswith("c_"): continue
  r=D[t["port"]];ent=int(r["ent"][1:])
  bs=[int(x[1:]) for x in t["path"] if x.startswith("b")];i=bs.index(ent);sub=bs[i:]
  L=sum(man((N[str(a)]["x"],N[str(a)]["y"]),(N[str(b)]["x"],N[str(b)]["y"])) for a,b in zip(sub,sub[1:]))
  Lreq=sum(man(N[str(a)]["req_xy"],N[str(b)]["req_xy"]) for a,b in zip(sub,sub[1:]))
  disp=sum(man((N[str(a)]["x"],N[str(a)]["y"]),N[str(a)]["req_xy"]) for a in sub)
  G[reg[t["part"]]].append((r["tree"]-r["ent_arr"],L,Lreq,disp,len(sub)))
cors=[];spL=[];spR=[];rows=[]
for g,L in G.items():
  a=[x[0] for x in L];l=[x[1] for x in L];q=[x[2] for x in L]
  spL.append(max(l)-min(l));spR.append(max(q)-min(q))
  if len(set(l))>1: cors.append(st.correlation(a,l))
  rows.append((max(a)-min(a),max(l)-min(l),max(q)-min(q),max(x[3] for x in L),st.median(x[4] for x in L)))
print("c_ regions",len(G),"corr(arrival, placed path length) median",round(st.median(cors),3))
print("placed path-length spread um med/max",st.median(spL),max(spL)," planned(req) spread med/max",st.median(spR),max(spR))
print("max node displacement med",st.median(r[3] for r in rows),"median nodes/path",st.median(r[4] for r in rows))
print("arrival spread med",st.median(r[0] for r in rows))
