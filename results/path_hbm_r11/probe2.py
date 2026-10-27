import sys,json,time,copy,math
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import hbm_r10_delta as R10, hbm_r9_delta as R9
P=json.load(open("/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks/die_plan.json"))
tn,part=sys.argv[2],sys.argv[3]; H=float(sys.argv[4]); b=float(sys.argv[5]); kcc=int(sys.argv[6]); ccmin=1000.0
t=P["partition_types"][tn]; W,H0=t["outline_um"]
bi=R10.bus_intervals(P,part,t); st,_=R10.resolve_lanes(t,bi,log=lambda *a:None)
R10.place_pins(st,W,H0,6.0); t1=dict(t,internal_stations=st)
Q=R9.plan_quadrants(t1,2,bounds=[R9.HR.sn(b)],dist_by_x=True)
def face(p): return p[1]<=.5 or p[1]>=H-.5 or p[0]<=.5 or p[0]>=W-.5
out=None
for k in range(1,9):
  try: cores,s2,infos,stats=R9.realise(t1,Q,H,kx=k,route=False)
  except ValueError: print(f"{tn} H {H} b {b} kcc {kcc} nopack"); sys.exit()
  R10.place_pins(s2,W,H,6.0,Hscale=H/H0); R10.chain_we(s2,W,k)
  ncc=0
  if kcc>1:
    for s in s2:
      if face(s["from_um"]) or face(s["to_um"]) or s.get("serial_k"): continue
      if abs(s["from_um"][0]-s["to_um"][0])+abs(s["from_um"][1]-s["to_um"][1])>ccmin:
        s["bits_parallel"]=s["bits"]; s["bits"]=math.ceil(s["bits"]/kcc); s["serial_k"]=kcc; ncc+=1
  u=R9.cut(dict(outline_um=[W,H],hard_cores=cores,internal_stations=s2))["blocked"]
  out=(k,u)
  if max(u['x']['max_use'],u['y']['max_use'])<=0.6: break
k,u=out
segs=[R10.profile(W,H,dict(hard_cores=cores,internal_stations=s2),a,c) for a,c in ((0,R9.HR.sn(b)),(R9.HR.sn(b),W))]
print(f"{tn} H {H} b {b} kcc {kcc} k {k} x {u['x']['max_use']} y {u['y']['max_use']} seg "+" ".join(f"({s['x'].get('max_use')},{s['y'].get('max_use')})" for s in segs)+f" ncc {ncc} nser {stats['serialised']} fill {[infos[i]['fill'] for i in infos]}",flush=True)
