"""Finite positive-buffer SOURCE clock graph; no actual CTS or phase claim."""
import json,gzip,collections,math,hashlib
from pathlib import Path
P=Path(__file__).resolve().parents[1];O=P/'out';I=P/'input';plan=json.load(gzip.open(O/'site_plan.json.gz','rt'));native=json.load(gzip.open(I/'native_pin_geometry.json.gz','rt'));old=json.loads((I/'positions.json').read_text());u=native['units'];contacts={p['canonical_cell']:p for p in native['pins'] if p['role']=='CLOCK'};assert len(contacts)==2904
bycanonical={c['canonical_cell']:c for c in plan.values()};oldname={p['canonical_cell']:p['cell'] for p in native['pins']}
def pin(c):
 p=contacts[c];_,b=max(p['shapes'],key=lambda z:(z[1][2]-z[1][0])*(z[1][3]-z[1][1]));q=((b[0]+b[2])/2/u,(b[1]+b[3])/2/u);ob=old['insts'][oldname[c]];nb=bycanonical[c];a=ob['bbox'];z=nb['bbox_dbu'];x=q[0]+(z[0]-a[0])/u
 y=q[1]+(z[1]-a[1])/u if ob['orient']==nb['orient'] else (z[1]+z[3])/2/u-(q[1]-(a[1]+a[3])/2/u)
 return x,y
ffxy={c:pin(c) for c in contacts};groups=collections.defaultdict(list)
for c in contacts:groups[bycanonical[c]['cohort']].append(c)
slots=[(64.8+k*1.674,56.16+r*.270) for r in range(104) for k in range(6)];nodes={};edges={};leafmap={};reserved=set()
def place(name,target,role):
 # Exact native BUF24 width1.62, height.270; all source sites/rows kept.
 k=min((k for k in range(len(slots)) if k not in reserved),key=lambda k:(abs(slots[k][0]+.81-target[0])+abs(slots[k][1]+.135-target[1]),k));reserved.add(k);x,y=slots[k]
 nodes[name]=dict(master='BUFx24_ASAP7_75t_R',bbox_um=[x,y,x+1.62,y+.270],role=role,model_port_center_um=[x+.81,y+.135],pin_access='Exact native A/Y MPin access remains required; center approximation prices source graph, no ideal clock')
 return name
root=place('clock_root',(70.2,70.2),'root');edges[root]=[]
for g,ffs in sorted(groups.items()):
 pts=[ffxy[f] for f in ffs];target=(sum(x for x,y in pts)/len(pts),sum(y for x,y in pts)/len(pts));regional=place('regional:'+g,target,'regional');edges[root].append(regional);edges[regional]=[]
 ffs.sort(key=lambda f:(ffxy[f][1],ffxy[f][0],f))
 for i in range(math.ceil(len(ffs)/32)):
  fs=ffs[i*32:(i+1)*32];pts=[ffxy[f] for f in fs];target=(sum(x for x,y in pts)/len(pts),sum(y for x,y in pts)/len(pts));leaf=place('leaf:'+g+':'+str(i),target,'leaf');edges[regional].append(leaf);edges[leaf]=fs;leafmap[leaf]=fs
assert len(nodes)==139 and len(leafmap)==111 and sum(map(len,leafmap.values()))==2904
assert sorted(f for fs in leafmap.values() for f in fs)==sorted(contacts)
assert max(map(len,edges.values()))<=32
assert all(64.8-1e-9<=n['bbox_um'][0] and n['bbox_um'][2]<=75.6+1e-9 and 56.16<=n['bbox_um'][1] and n['bbox_um'][3]<=84.24+1e-9 for n in nodes.values())
def mst(ps):
 chosen={0};remaining=set(range(1,len(ps)));es=[]
 while remaining:
  d,a,b=min((abs(ps[a][0]-ps[b][0])+abs(ps[a][1]-ps[b][1]),a,b) for a in chosen for b in remaining);es.append([a,b,d]);chosen.add(b);remaining.remove(b)
 return es
led=[]
for d,ss in edges.items():
 ps=[nodes[d]['model_port_center_um']]+[nodes[s]['model_port_center_um'] if s in nodes else ffxy[s] for s in ss];es=mst(ps);length=sum(e[2] for e in es)
 led.append(dict(driver=d,sinks=ss,points_um=ps,rectilinear_MST_edges=es,wire_length_um=length,nominal_clock_wire_cap_fF=length*.145426,nominal_clock_wire_R_sum_kohm=length*.0214161,via_count='OPEN; native A/Y+CLK access, clock track ownership and real CTS required'))
clock=json.loads((I/'native_clock_cell.json').read_text());wire=sum(z['wire_length_um'] for z in led);cost=dict(scope='SOURCE candidate only; does not modify frozen11145cell design or claim CTS, phase, earlyCQ, hold, setup',siteplan_sha256=hashlib.sha256((O/'site_plan.json.gz').read_bytes()).hexdigest(),nodes=nodes,edges=edges,native_FF_sink_points_um=ffxy,ledger=led,summary=dict(root=1,regional=27,leaf=111,buffers=139,max_fanout=max(map(len,edges.values())),native_clock_sinks=2904,area_um2=139*.4374,spine_area_um2=303.264,spine_average_fill=139*.4374/303.264,TT_buffer_input_cap_fF=139*clock['input_A_cap_fF'],FF_buffer_input_cap_fF=139*(690.94775/265),native_TT_FF_sink_cap_fF=[1378.633344,1515.91704],nominal_clock_RSMT_wire_um=wire,nominal_clock_wire_cap_fF=wire*.145426,source_clock_pin_to_root='Fixed W(0,70.2) source ingress outside graph wireledger; real ingress/access/cap/phase OPEN',max139term_PGcost=278,max265budgetterm_PGcost=530,physical_native_PG_binding='Future cells require a92 MTerm-complete domain binding AT BIRTH and actual conductor/contact/short audit; existing22290 contacts do not cover new clock cells',clocktrack_reservation='111 leaf longH trunks <=128 separately recorded conservative band Hray reservations; actual chosen tree/landing/clockroute OPEN',budget265area_um2=265*.4374,remaining_budget_buffers=126),open=['Actual A/Y native pin access and actual per-corner load axes','Source ingress wire/vias and genuine PGclear simultaneous clock geometry','Actual CTS/clockcap/slew/insertion/spread TT+FF','Real parent clock reference/phase/earlyCQ and IO hold'])
(O/'CLOCK_CANDIDATE.json').write_text(json.dumps(cost,indent=2)+'\n');print(json.dumps(cost['summary']))
