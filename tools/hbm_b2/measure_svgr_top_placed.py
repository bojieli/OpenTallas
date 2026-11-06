import odb,json,os,math,collections
D=odb.dbDatabase.create(); odb.read_db(D,os.environ['SVGR_ODB']); b=D.getChip().getBlock(); U=b.getDbUnitsPerMicron()
def box(r): return [r.xMin()/U,r.yMin()/U,r.xMax()/U,r.yMax()/U]
def area(r): return r.dx()*r.dy()/U**2
core=b.getCoreArea(); counts=collections.Counter(); areas=collections.Counter(); masters=collections.Counter(); macros=[]; points=[]; pg=[]
for i in b.getInsts():
 m=i.getMaster(); typ=str(m.getType()); name=m.getName(); masters[(name,typ)]+=1
 kind='macro' if m.isBlock() else ('tap' if 'WELLTAP' in typ or name.upper().startswith('TAP') else ('fill' if 'SPACER' in typ or name.upper().startswith('FILL') else 'functional'))
 counts[kind]+=1; areas[kind]+=m.getWidth()*m.getHeight()/U**2
 if kind=='macro': macros.append({'name':i.getName(),'master':name,'box':box(i.getBBox())})
 if kind=='functional': points.append({'x':i.getLocation()[0]/U,'y':i.getLocation()[1]/U,'w':m.getWidth()/U,'h':m.getHeight()/U,'placed':i.isPlaced()})
 for p in i.getITerms():
  s=str(p.getMTerm().getSigType())
  if s in ('POWER','GROUND'):
   n=p.getNet()
   if n is None or str(n.getSigType())!=s: pg.append({'instance':i.getName(),'pin':p.getMTerm().getName(),'expected':s,'net':None if n is None else n.getName()})
rows_area=0; legal_area=0; nrows=0; badrows=[]
for r in b.getRows():
 q=r.getBBox(); s=r.getSite(); n=r.getSiteCount(); w=s.getWidth(); h=s.getHeight(); step=(q.dx()-w)/(n-1) if n>1 else w
 if q.dy()!=h or step<=0: badrows.append(r.getName()); continue
 nrows+=1; rows_area+=n*w*h/U**2; intervals=[]
 for m in macros:
  lo,bot,hi,top=[v*U for v in m['box']]; halo=4.32*U
  if q.yMax()<=bot-halo or q.yMin()>=top+halo: continue
  a=max(0,math.floor((lo-halo-w-q.xMin())/step)+1); z=min(n-1,math.ceil((hi+halo-q.xMin())/step)-1)
  if a<=z: intervals.append((a,z))
 merged=[]
 for a,z in sorted(intervals):
  if merged and a<=merged[-1][1]+1: merged[-1][1]=max(z,merged[-1][1])
  else: merged.append([a,z])
 legal_area+=(n-sum(z-a+1 for a,z in merged))*w*h/U**2
clock=[]
for t in b.getBTerms():
 if t.getName()=='stream_clk':
  for p in t.getBPins():
   for z in p.getBoxes(): clock.append({'layer':z.getTechLayer().getName(),'box':box(z)})
def overlap(a,c): return min(a[2],c[2])>max(a[0],c[0]) and min(a[3],c[3])>max(a[1],c[1])
hits=[]; inspected=collections.Counter(); nearest=None
for n in b.getNets():
 if str(n.getSigType()) not in ('POWER','GROUND'): continue
 for sw in n.getSWires():
  for z in sw.getWires():
   if z.isVia():
    v=z.getTechVia() or z.getBlockVia(); layers=[v.getTopLayer().getName(),v.getBottomLayer().getName()]
    if 'M5' not in layers: continue
    kind='via_envelope'
   else:
    if z.getTechLayer().getName()!='M5': continue
    kind='wire'
   inspected[kind]+=1; bb=box(z)
   for c in clock:
    if c['layer']!='M5': continue
    cb=c['box']; dx=max(cb[0]-bb[2],bb[0]-cb[2],0); dy=max(cb[1]-bb[3],bb[1]-cb[3],0); distance=math.hypot(dx,dy)
    if nearest is None or distance<nearest['edge_distance_um']: nearest={'edge_distance_um':distance,'axis_gap_um':[dx,dy],'net':n.getName(),'kind':kind,'box':bb}
    if overlap(cb,bb): hits.append({'net':n.getName(),'kind':kind,'box':bb})
a=areas['functional']; out={'odb':os.environ['SVGR_ODB'],'core_box':box(core),'core_area_um2':area(core),'counts':dict(counts),'areas_um2':dict(areas),'nonmacro_core_util':a/(area(core)-areas['macro']),'actual_row_site_area_um2':rows_area,'post_4p32_halo_row_site_area_um2':legal_area,'post_halo_row_util':a/legal_area,'row_count':nrows,'unsupported_rows':badrows,'macros':macros,'pg_logical_missing_or_wrong_net':pg,'clock_pins':clock,'clock_M5_PG_intersections':hits,'clock_PG_shapes_inspected':dict(inspected),'clock_nearest_M5_PG_shape_or_via_envelope':nearest,'master_inventory':[{'master':k[0],'type':k[1],'count':v} for k,v in sorted(masters.items())],'unplaced_functional':sum(not p['placed'] for p in points),'cells':points}
with open(os.environ['SVGR_OUT'],'w') as f: json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in out.items() if k not in ('cells','master_inventory','macros')},indent=2))
