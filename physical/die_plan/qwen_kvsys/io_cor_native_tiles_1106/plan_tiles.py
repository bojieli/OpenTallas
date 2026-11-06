import odb,re,json,pathlib,collections,math,hashlib
R=pathlib.Path('/out');D=odb.dbDatabase.create();odb.read_db(D,'/kit/run/results/asap7/dp_kv3_io_cor/base/2_floorplan.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron();base=json.loads((R/'bands.json').read_text());targets=['ft4_i','ft17_i','ft15_i','ft19_i'];newbands={'ft4_i':[1165.44,159.392,1261.44,239.392],'ft17_i':[1072.56,17.28,1168.56,97.28],'ft15_i':[860.96,17.28,940.96,113.28],'ft19_i':[17.28,606.496,113.28,686.496]};by={i.getName():i for i in b.getInsts()};owners=collections.defaultdict(set);seed={};kind={};held=set();allmembers={k:[] for k in targets};normal=lambda n:n.replace(chr(92),'')
facefile=pathlib.Path('/kit/run/results/asap7/dp_kv3_io_cor/base/ot_face_flops.txt')
for line in facefile.read_text().splitlines():
 a=line.split('\t')
 if len(a)>1 and not a[1].startswith('cland:ring:'):held.add(a[0])
for i in b.getInsts():
 name=i.getName();nm=normal(name);ma=re.search(r'u_cland_(ft\d+_i)/',nm)
 if not ma or ma[1] not in targets:continue
 f=ma[1];allmembers[f].append(i)
 if name in held:continue
 a=re.search(r'/u_ring\.s_d\[(\d+)\]\[(\d+)\]',nm)
 c=re.search(r'/u_ring\.dch\[(\d+)\]\.u_dsel/',nm)
 if a:
  if 'DFFLQN' not in i.getMaster().getName():raise Exception(('unexpected write FF master',name))
  j=int(a[2])//64
  if int(a[1])>=4 or j>=9:raise Exception(name)
  seed[name]=(f,j);kind[name]='write_ff'
 elif c:
  j=int(c[1]);
  if j>=9:raise Exception(name)
  seed[name]=(f,j);kind[name]='read_ff' if 'DFF' in i.getMaster().getName() else 'mux'
# Exact bounded data-fanin ownership. Shared decode/control cones remain held.
def walk(net,f,tile,depth,seen):
 if net is None or depth>6:return
 nn=net.getName()
 if nn in seen:return
 seen.add(nn)
 if net.getBTerms():return
 ds=[x for x in net.getITerms() if x.getMTerm().getIoType()=='OUTPUT']
 if len(ds)!=1:return
 i=ds[0].getInst();n=i.getName();nm=normal(n)
 if f'u_cland_{f}/' not in nm or 'DFF' in i.getMaster().getName() or n in held:return
 if n in seed:
  if seed[n]!=(f,tile):return
 else:owners[n].add((f,tile))
 for p in i.getITerms():
  if p.getMTerm().getIoType()=='INPUT' and p.getMTerm().getSigType() not in ('CLOCK','POWER','GROUND'):walk(p.getNet(),f,tile,depth+1,seen)
for n,(f,tile) in list(seed.items()):
 i=by[n]
 pins=[i.findITerm('D')] if 'DFF' in i.getMaster().getName() else [p for p in i.getITerms() if p.getMTerm().getIoType()=='INPUT']
 for p in pins:
  if p is not None:walk(p.getNet(),f,tile,0,set())
selected=dict(seed)
for n,ls in owners.items():
 if len(ls)==1:selected[n]=next(iter(ls));kind[n]='write_data_logic'
# Ensure selected write-D cones do not move explicitly protected cells or other rings.
assert not (set(selected)&held)
# Raw plan-band/outline/HARD-blockage legality, other native ring reservations unchanged.
for f,rect in newbands.items():
 x0,y0,x1,y1=rect
 assert 0<x0<x1<1278.72 and 0<y0<y1<1036.8
 for k,v in base['bands'].items():
  if k in targets:continue
  a,c,dd,e=v['rect_um']
  if min(x1,dd)>max(x0,a) and min(y1,e)>max(y0,c):raise Exception(('other band overlap',f,k))
 for block in b.getBlockages():
  if block.isSoft():continue
  q=block.getBBox();a,c,dd,e=[z/u for z in (q.xMin(),q.yMin(),q.xMax(),q.yMax())]
  if min(x1,dd)>max(x0,a) and min(y1,e)>max(y0,c):raise Exception(('hard blockage overlap',f,rect,[a,c,dd,e]))
regions=[];receipt={};manifest=[];held_rows=[]
for f in targets:
 rect=newbands[f];x0,y0,x1,y1=rect;tw=(x1-x0)/3;th=(y1-y0)/3;boxes=[[x0+col*tw+1,y0+row*th+1,x0+(col+1)*tw-1,y0+(row+1)*th-1] for row in range(3) for col in range(3)];pinpts=collections.defaultdict(list)
 for p in b.getBTerms():
  m=re.fullmatch(f+r'\[(\d+)\]',normal(p.getName()))
  if m:
   bb=p.getBBox();pinpts[int(m[1])//64].append(((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u))
 if set(pinpts)!=set(range(9)):raise Exception(('missing native pin chunk',f,sorted(pinpts)))
 centers=[((a+c)/2,(bb+dd)/2) for a,bb,c,dd in boxes];means=[(sum(a for a,c in pinpts[j])/len(pinpts[j]),sum(c for a,c in pinpts[j])/len(pinpts[j])) for j in range(9)]
 # Deterministic exact 9x9 minimum Manhattan assignment, no dependency on scipy.
 dp={0:(0,[])}
 for j in range(9):
  nd={}
  for mask,(cost,order) in dp.items():
   for q,(x,y) in enumerate(centers):
    if mask>>q&1:continue
    nc=cost+abs(x-means[j][0])+abs(y-means[j][1]);nm=mask|1<<q
    if nm not in nd or nc<nd[nm][0]:nd[nm]=(nc,order+[q])
  dp=nd
 order=dp[(1<<9)-1][1];totalarea=0;maxhop=0;counts=collections.Counter()
 for j,q in enumerate(order):
  names=sorted(n for n,v in selected.items() if v==(f,j));box=boxes[q];area=sum(by[n].getMaster().getWidth()*by[n].getMaster().getHeight()/u/u for n in names);totalarea+=area
  for n in names:counts[kind[n]]+=1;manifest.append([n,by[n].getMaster().getName(),f,j])
  corners=[(box[a],box[c]) for a in (0,2) for c in (1,3)];hop=max(abs(px-x)+abs(py-y) for px,py in pinpts[j] for x,y in corners);maxhop=max(maxhop,hop)
  if hop>405:raise Exception(('capture reach',f,j,hop))
  regions.append(dict(name=f'ot_rg_native_{f}_{j}',box_um=box,insts=names,area_um2=area,fill=area/((box[2]-box[0])*(box[3]-box[1])),max_pin_to_tile_l1_um=hop))
 for i in allmembers[f]:
  if i.getName() not in selected:held_rows.append([i.getName(),i.getMaster().getName()])
 receipt[f]=dict(selected=sum(counts.values()),selected_roles=dict(counts),held=len(allmembers[f])-sum(counts.values()),box_um=rect,selected_area_um2=totalarea,max_pin_to_tile_l1_um=maxhop)
spec=dict(schema='opentallas.region_guide.v1',die_um=[0,0,1278.72,1036.8],regions=regions,tile_um=None,source='exact native s_d[slot][bit] and dch[N], unique bounded data-fanin; no RTL/cycle changes')
(R/'native_tiles_regions.json').write_text(json.dumps(spec,indent=1));(R/'native_tiles_manifest.tsv').write_text('\n'.join('\t'.join(map(str,row)) for row in sorted(manifest))+'\n');(R/'native_tiles_held.tsv').write_text('\n'.join('\t'.join(row) for row in sorted(held_rows))+'\n');(R/'native_tiles_receipt.json').write_text(json.dumps(dict(families=receipt,regions=len(regions),moved=len(manifest),held=len(held_rows),protected_face_cells=len(held),source='2_floorplan.odb',no_connectivity_edits=True,zero_added_cycles=True),indent=1))
print(json.dumps(receipt,indent=1));print('REGIONS',len(regions),'MOVED',len(manifest),'HELD',len(held_rows),'MAX_FILL',max(x['fill'] for x in regions))
