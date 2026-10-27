import sys,json,time,copy
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import hbm_r10_delta as R10, hbm_r9_delta as R9
P=json.load(open("/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks/die_plan.json"))
tn,part=sys.argv[2],sys.argv[3]; H=float(sys.argv[4]); k=int(sys.argv[5])
t=P["partition_types"][tn]; W,H0=t["outline_um"]
bi=R10.bus_intervals(P,part,t); st,_=R10.resolve_lanes(t,bi,log=lambda *a:None)
R10.place_pins(st,W,H0,6.0); t1=dict(t,internal_stations=st)
print(tn,"W",W,"H0",H0,"lane bound",R10.lane_bounds(st,W,2))
for b in [float(x) for x in sys.argv[6].split(",")]:
  t0=time.time()
  Q=R9.plan_quadrants(t1,2,bounds=[R9.HR.sn(b)],dist_by_x=True)
  try: cores,s2,infos,stats=R9.realise(t1,Q,H,kx=k,route=False)
  except ValueError as e: print(b,"nopack",e); continue
  R10.place_pins(s2,W,H,6.0,Hscale=H/H0); R10.chain_we(s2,W,k)
  u=R9.cut(dict(outline_um=[W,H],hard_cores=cores,internal_stations=s2))["blocked"]
  segs=[R10.profile(W,H,dict(hard_cores=cores,internal_stations=s2),a,c) for a,c in ((0,R9.HR.sn(b)),(R9.HR.sn(b),W))]
  print(f"b {b} x {u['x']['max_use']} y {u['y']['max_use']} @y {u['y'].get('at_um')} seg "+" ".join(f"({s['x'].get('max_use')},{s['y'].get('max_use')})" for s in segs)+f" fill {[infos[i]['fill'] for i in infos]} {time.time()-t0:.1f}s",flush=True)
