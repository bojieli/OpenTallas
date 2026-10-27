import sys,json,pathlib,collections
O=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-pd2-2000');sys.path.insert(0,str(O/'modelsrc/tools/die_plan'));import schema as S,gen_phys as G,taps as T
f=str(O/'plandir/die_plan_phy_clock.json');P=S.Plan(S.load(f),f);rows=[]
for pn,p in P.parts.items():
 if not pn.startswith('lk_'):continue
 tn=p['type'];ck=P.types[tn]['clock'];raw=G.clock_pins(P,tn);boxes=ck.get('keepouts_um',[]);bad=[dict(name=n,xy=[x,y]) for n,x,y in raw if any(a<x<c and b<y<d for a,b,c,d in boxes)];sinks=T.sink_sites(P,tn);loads=T.tap_loads([(x,y) for n,x,y in raw],sinks)
 rows.append(dict(part=pn,type=tn,taps=len(raw),tap_inside_phy=bad,max_load=max(x[0] for x in loads),max_sink_distance_um=max(x[1] for x in loads),empty_taps=sum(x[0]==0 for x in loads),sinks=sum(q[2] for q in sinks)))
 print(json.dumps(rows[-1]),flush=True)
json.dump(dict(status='CANDIDATE_CENSUS',rows=rows),open(O/'phy_clock_census.json','w'),indent=1)
