import odb,json,re,collections,time
print('BEGIN',time.time(),flush=True)
db=odb.dbDatabase.create();odb.read_db(db,'/input/replay.odb');b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();insts=b.getInsts()
kind={}; parents=[]; rank=bytearray(); masks=[]; areas=[]; comb_names=[]; seq_counts=collections.Counter();seq_areas=collections.Counter();ties=set();total_std=0;total_std_area=0
for i in insts:
 m=i.getMaster();nm=m.getName();name=i.getName();oid=i.getId();area=m.getWidth()*m.getHeight()/u**2
 if m.isBlock():kind[oid]=('s',16);continue
 total_std+=1;total_std_area+=area
 hit=re.search(r'u_astk_u_strip_u_strip_g_ep_p_g_ex_([0-3])_u_ex',name)
 if re.match(r'^(?:S?DFF|ICG|LATCH)',nm):
  group=int(hit.group(1)) if hit else -1;mask=1<<group if group>=0 else 16;kind[oid]=('s',mask);seq_counts[group]+=1;seq_areas[group]+=area
 elif re.match(r'^(?:TIE|FILL|TAP|DECAP)',nm):kind[oid]=('t',0);ties.add(oid)
 else:
  idx=len(parents);kind[oid]=('c',idx);parents.append(idx);rank.append(0);masks.append(0);areas.append(area);comb_names.append(name)
def root(i):
 while parents[i]!=i:
  parents[i]=parents[parents[i]];i=parents[i]
 return i
def union(a,c):
 a=root(a);c=root(c)
 if a==c:return a
 if rank[a]<rank[c]:a,c=c,a
 parents[c]=a;masks[a]|=masks[c]
 if rank[a]==rank[c]:rank[a]+=1
 return a
print('CELLS',len(insts),total_std,len(parents),dict(seq_counts),flush=True)
for z,n in enumerate(b.getNets()):
 if n.getSigType() in ('POWER','GROUND','CLOCK'):continue
 its=n.getITerms();comb=[];mask=0;skip=False
 for t in its:
  mt=t.getMTerm()
  if mt.getSigType()=='CLOCK' or re.fullmatch(r'(?:CLK|CK|GCLK|RCLK|WCLK)',mt.getName()):skip=True;break
  k,v=kind[t.getInst().getId()]
  if k=='t' and mt.getIoType()=='OUTPUT':skip=True;break
  if k=='c':comb.append(v)
  elif k=='s':mask|=v
 if skip or not comb:continue
 if n.getBTerms():mask|=16
 r=root(comb[0]);masks[r]|=mask
 for c in comb[1:]:r=union(r,c)
 if z%100000==0:print('NETS',z,flush=True)
cs=collections.Counter();ca=collections.Counter();other=collections.Counter()
for i in range(len(parents)):
 mask=masks[root(i)];g={1:0,2:1,4:2,8:3}.get(mask,-1)
 cs[g]+=1;ca[g]+=areas[i]
 if g<0:other[mask]+=1
rows=[]
for g in range(4):
 rows.append(dict(ex=g,sequential=seq_counts[g],exclusive_comb=cs[g],minimum_cells_removed=seq_counts[g]+cs[g],std_area_um2=round(seq_areas[g]+ca[g],4)))
res=dict(parent_total=len(insts),parent_std=total_std,parent_std_area_um2=total_std_area,ex=rows,remaining_parent_upper_bound=len(insts)-sum(r['minimum_cells_removed'] for r in rows),unattributed_comb_masks=other)
open('/out/attribution.json','w').write(json.dumps(res,indent=1)+'\n');print('RESULT',json.dumps(res),flush=True)
