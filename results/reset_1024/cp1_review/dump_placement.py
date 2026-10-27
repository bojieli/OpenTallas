import odb,json,os,math
p=os.environ['ODB'];db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();box=b.getDieArea()
cells=[];xy={};skip=0
for i in b.getInsts():
 m=i.getMaster();mn=m.getName();ty=str(m.getType())
 if ty in {'CORE_SPACER','CORE_WELLTAP'} or any(s in mn.upper() for s in ['TAPCELL','FILLER','DECAP']):skip+=1;continue
 x,y=i.getLocation();w,h=m.getWidth(),m.getHeight();name=i.getName();xy[name]=[(x+w/2)/u,(y+h/2)/u]
 cells.append([name,mn,(x+w/2)/u,(y+h/2)/u,w/u,h/u,str(i.getPlacementStatus())])
pins=[]
for bt in b.getBTerms():
 for bp in bt.getBPins():
  for r in bp.getBoxes():pins.append([bt.getName(),(r.xMin()+r.xMax())/(2*u),(r.yMin()+r.yMax())/(2*u),r.getTechLayer().getName()])
edges=[]
for n in b.getNets():
 name=n.getName()
 if str(n.getSigType()) in {'POWER','GROUND','CLOCK'} or name.startswith('clk') or 'rst' in name.lower():continue
 points=[]
 for it in n.getITerms():
  inst=it.getInst();nm=inst.getName()
  if nm in xy:points.append((nm,xy[nm]))
 if 1<len(points)<=4:
  for j,(a,pa) in enumerate(points):
   for c,pc in points[j+1:]:
    dist=abs(pa[0]-pc[0])+abs(pa[1]-pc[1])
    if dist>100:edges.append([dist,a,c,pa,pc,name])
edges.sort(reverse=True)
json.dump(dict(odb=p,die=[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u],cells=cells,pins=pins,edges=edges[:300],physical_cells_skipped=skip),open(os.environ['OUT'],'w'))
print('DUMP_PLACEMENT',len(cells),'active',skip,'physical skipped',len(edges),'segments>100um')
