"""Actual-provider static key rail lower-bound model, not a physical route.
Four distributed injectors, then two receiver walks (one per cohort/quarter).
Existing keybuf RX pin windows are over-dense; use actual old mean only as a
location estimate, preserving the need for coherent repin and exact bank homes.
"""
import hashlib,itertools,json,math,sys
from pathlib import Path
D,O=map(Path,sys.argv[1:3]);P=json.load(open(D/'die_plan.json'));O.mkdir(parents=True,exist_ok=True)
def xy(h,p):
 x,y=p;w,z=h['outline_um'];o=h.get('orient','R0')
 if o in ['MY','R180']:x=w-x
 if o in ['MX','R180']:y=z-y
 return [round(h['origin_um'][0]+x,6),round(h['origin_um'][1]+y,6)]
def point(h,name):
 ps=[p for p in json.load(open(D/h['pins_file'])) if p['name'].startswith(name+'[')];assert len(ps)==1099
 return xy(h,[sum(p['x']for p in ps)/len(ps),sum(p['y']for p in ps)/len(ps)])
def md(a,b):return sum(abs(x-y)for x,y in zip(a,b))
def leg(a,b,na,nb):
 L=md(a,b);edges=math.ceil(L/405-1e-9)
 return {'from':na,'to':nb,'from_um':a,'to_um':b,'manhattan_um':round(L,6),'wire_segments_min':edges,'extra_relay_edges_min':max(0,edges-1),'extra_relay_ff_min':1112*max(0,edges-1),'clock_region':'UNASSIGNED: actual GEN/clock geometry/CA required','ca_cycles':'NOT PRICED: shared phase/OCV/droop model required'}
rep={'schema':'hbm.static-key-rail.estimate.v1','source_plan_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'scope':'ESTIMATE ONLY: native source fixed-slot merge; no runtime arbitration or credits; no route/clock/latency qualification','width_bits':1112,'producer_order':['u_svg_Q1','u_svg_Q3','u_svg_Q2','u_svg_Q0'],'halves':{},'known_holds':['Source SVG and keybuf pin6 repairs not yet composed; centroids are existing invalid-density template location estimates.','Existing SVG internal station metadata is reversed: no source coverage; old North and new South receive paths both need materialization.','Distances are Manhattan centreline lower bounds; FF bank/clock-driver/PG row sites and wide M6/M7 corridor cuts not solved.','Every multi-region link needs actual count-aligned margin check and model cycles. No guessed clock regions or K.','Do not use these lower bounds as production GO offsets. Actual source addresses/controller/VM19 programme remain distinct gates.']}
for tn in ['q_hub_nw','q_hub_ne']:
 t=P['partition_types'][tn];hs={h['inst']:h for h in t['hard_cores']};pts={n:point(hs[n],'sm_packet')for n in rep['producer_order']};rall={q:{f'u_mu_keybuf_0_s{i}__q{q}':point(hs[f'u_mu_keybuf_0_s{i}__q{q}'],'key_in')for i in range(4)}for q in [0,1]}
 candidates=[]
 for trial in itertools.permutations(pts):
  producer=sum(md(pts[a],pts[b])for a,b in zip(trial,trial[1:]))
  rsum=sum(min(md(pts[trial[-1]],r[o[0]])+sum(md(r[a],r[b])for a,b in zip(o,o[1:]))for o in itertools.permutations(r))for r in rall.values())
  candidates.append((producer+rsum,trial))
 total,order=min(candidates)
 legs=[leg(pts[a],pts[b],a,b)for a,b in zip(order,order[1:])];suffix={order[-1]:0}
 for l in legs[::-1]:suffix[l['from']]=l['extra_relay_edges_min']+suffix[l['to']]
 receivers={};endpoint=pts[order[-1]]
 for q in [0,1]:
  rpts={f'u_mu_keybuf_0_s{i}__q{q}':point(hs[f'u_mu_keybuf_0_s{i}__q{q}'],'key_in')for i in range(4)}
  cost,path=min((md(endpoint,rpts[o[0]])+sum(md(rpts[a],rpts[b])for a,b in zip(o,o[1:])),o)for o in itertools.permutations(rpts))
  seg=[];prev=order[-1];a=endpoint
  for n in path:seg.append(leg(a,rpts[n],prev,n));prev,a=n,rpts[n]
  receivers[f'q{q}']={'order':path,'manhattan_um':round(cost,6),'legs':seg,'extra_relay_edges_sum_min':sum(l['extra_relay_edges_min']for l in seg)}
 rep['halves'][tn]={'estimated_total_rail_wire_um':round(total,6),'chosen_order':order,'producers':pts,'producer_legs':legs,'producer_extra_path_edges_min':suffix,'producer_wire_um':sum(l['manhattan_um']for l in legs),'receivers':receivers}
(O/'estimate.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps({tn:{'producer_wire_um':h['producer_wire_um'],'producer_path_extra_min':h['producer_extra_path_edges_min'],'receiver_walks':{q:(r['manhattan_um'],r['extra_relay_edges_sum_min'])for q,r in h['receivers'].items()}}for tn,h in rep['halves'].items()},indent=1))
