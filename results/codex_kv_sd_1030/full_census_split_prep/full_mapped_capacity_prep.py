import csv,json,re,sys,collections
from pathlib import Path
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r/'src/tools/die_plan'));import taps
k=r/'kits_anchor_v2/kv3_sys_SD';rows=list(csv.DictReader(open(k/'mapped_ff_census.tsv'),delimiter='\t'));old={}
for s in (r/'geom_sdpg_after/geom.tsv').read_text().splitlines():
 a=s.split('\t')
 if a[0]=='C' and a[2]=='S':old[a[-1]]=[(float(a[4])+float(a[6]))/2,(float(a[5])+float(a[7]))/2]
positions=json.load(open(r/'phy_wide_data_ff_rows.json'))['positions']
s=(k/'landing_placement.tcl').read_text()
groups=[]
for m in re.finditer(r'^\s*\{(u_\S+) \{([0-9. -]+)\} ([^}]+)\}',s,re.M):
 x,y,X,Y=map(float,m[2].split());groups.append((m[1],[(x+X)/2,(y+Y)/2],m[3]))
resets=[]
s=(k/'reset_tree.tcl').read_text()
for m in re.finditer(r'^rtr_place(?:_opt)? \S+ \{([^}]+)\} ([0-9.]+) ([0-9.]+) ',s,re.M):
 pat=m[1];key=re.search(r'\*(u_[A-Za-z0-9_]+)\[',pat)
 if key:resets.append((key[1],[float(m[2]),float(m[3])],'current reset/run geometry'))
missing=[];out=[];basis=collections.Counter()
for row in rows:
 n=row['instance'];xy=None;src=''
 # Current generated anchors supersede SAME-NAMED old control cells too.
 for key,pt,kind in resets:
  if re.search(r'(?:^|[./])'+re.escape(key)+r'[./]',n):xy=pt;src=kind;break
 for key,pt,kind in groups:
  if re.search(r'(?:^|[./])'+re.escape(key)+r'[./]',n):xy=pt;src='current group centre:'+kind;break
 if n in positions:xy=positions[n]['xy_um'];src='current proposed data-FF row'
 if xy is None and n in old:xy=old[n];src='same-name old actual DPL position (unqualified for new)'
 if xy is None:missing.append(row);continue
 basis[src]+=1;out.append(dict(row,xy_um=xy,basis=src))
p=json.load(open(r/'plan_of_record/plan_c_sd_pg_anchor_v2.json'));ck=p['partition_types']['kv3_sys_SD']['clock'];ts=[(x['name'],*x['xy']) for x in ck['taps']]
primary=[x for x in out if x['clock_net']=='clk'];ss=[x['xy_um']+[1] for x in primary]
load,far,asg=taps.assign(ts,ss,2400,400,max_distance_um=400)
bad=[{'root':t[0],'load':n,'max_L1_um':d} for t,n,d in zip(ts,load,far) if n>2400 or d>400 or not n]
result={'qualification':False,'kind':'EXHAUSTIVE mapped FF census with preparatory XY assignments. Group centres are capacity anchors, NOT legal placements; stale same-name DATA/logic XY fallbacks disclosed. Never a new G1/physical pass.','actual_mapped_ff':len(rows),'clock_domains':dict(collections.Counter(x['clock_net'] for x in rows)),'xy_bound_ff':len(out),'missing':missing,'primary_count':len(primary),'xy_basis_counts':dict(basis),'tap_capacity':[{ 'root':t[0],'load':n,'max_L1_um':d} for t,n,d in zip(ts,load,far)],'capacity_errors':bad,'primary_over_220_after_capacity_rebalance':sum(abs(x['xy_um'][0]-ts[j][1])+abs(x['xy_um'][1]-ts[j][2])>220 for x,j in zip(primary,asg))}
(r/'sd_r52_full_mapped_capacity_prep.json').write_text(json.dumps(result,indent=2))
(r/'sd_r52_full_mapped_xy_inventory.json').write_text(json.dumps(out,indent=1))
print(json.dumps(result,indent=2)[:12000])
