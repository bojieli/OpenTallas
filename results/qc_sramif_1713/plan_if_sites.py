import odb,os,json,re,collections,math
D=odb.dbDatabase.create();odb.read_db(D,os.environ['ODB']);b=D.getChip().getBlock();u=b.getDbUnitsPerMicron();root='/work';p=json.load(open(root+'/profile1713.json'))
def ff(i):return any(s in i.getMaster().getName() for s in ('DFF','DHL','SDF'))
def walk(net,back):
 q=collections.deque([(net,0)]);seen=set();hit={}
 while q:
  n,depth=q.popleft()
  if n is None or n.getName() in seen:continue
  seen.add(n.getName())
  for t in n.getITerms():
   if (t.isOutputSignal() if back else t.isInputSignal()):
    i=t.getInst();m=i.getMaster()
    if m.isBlock():continue
    if ff(i):hit[i.getName()]=i;continue
    buf=bool(re.match(r'^(BUF|INV|HB)',m.getName()));nd=depth+(not buf)
    if nd>4:continue
    for z in i.getITerms():
     if (z.isInputSignal() if back else z.isOutputSignal()) and z.getMTerm().getSigType()=='SIGNAL':q.append((z.getNet(),nd))
 return list(hit.values())
macros=sorted((i for i in b.getInsts() if i.getMaster().isBlock()),key=lambda i:i.getName());assert len(macros)==4
links=[];groups=collections.defaultdict(dict);exceptions=[];conflicts=[]
for bank,(i,s) in enumerate(zip(macros,p['macro_sites'])):
 i.setOrient('R0');i.setLocation(round(s['x']*u),round(s['y']*u))
 for t in i.getITerms():
  pn=t.getMTerm().getName();direction='write' if re.match(r'^(r_ce_in|r_addr_in|w_ce_in|w_addr_in|wd_in)(\[|$)',pn) else 'read' if pn.startswith('rd_out[') else None
  if direction is None:continue
  ok,x,y=t.getAvgXY();assert ok
  hits=walk(t.getNet(),direction=='write')
  if not hits:
   exceptions.append(dict(macro=i.getName(),pin=pn,direction=direction,reason='NO_CONNECTED_FF',net=t.getNet().getName() if t.getNet() else None));continue
  # Exact macro-MIF interface should be a single first FF. Multiple is an explicit gate failure.
  if len(hits)!=1:conflicts.append(dict(macro=i.getName(),pin=pn,registers=[z.getName() for z in hits]));continue
  z=hits[0];side='W' if x/u < s['x']+s['w']/2 else 'E';g=groups[(bank,side)]
  r=g.setdefault(z.getName(),dict(inst=z,points=[],links=[],bank=bank,side=side,macro=i.getName()))
  r['points'].append((x/u,y/u));r['links'].append(len(links));links.append(dict(macro=i.getName(),pin=pn,direction=direction,register=z.getName(),pin_um=[x/u,y/u]))
placements={};private=[];overlaps=[]
for (bank,side),regs in groups.items():
 s=p['macro_sites'][bank];used=set();items=sorted(regs.items(),key=lambda kv:sum(y for x,y in kv[1]['points'])/len(kv[1]['points']))
 for name,r in items:
  i=r['inst'];m=i.getMaster();w=m.getWidth()/u;h=m.getHeight()/u;cy=sum(y for x,y in r['points'])/len(r['points'])
  rows=range(math.ceil((s['y']+1.08)/.27),math.floor((s['y']+s['h']-h-1.08)/.27)+1)
  row,col=min(((rr,cc) for rr in rows for cc in range(3) if (rr,cc) not in used),key=lambda rc:(abs(rc[0]*.27+h/2-cy),rc[1]))
  used.add((row,col));x=s['x']-6.48-(col+1)*w if side=='W' else s['x']+s['w']+6.48+col*w;x=round(x/.054)*.054;y=row*.27
  if name in placements:conflicts.append(dict(register=name,reason='SHARED_BANK_OR_SIDE'))
  placements[name]=dict(x=x,y=y,w=w,h=h,bank=bank,side=side,role='macro_interface',macro=r['macro'])
  for k in r['links']:
   pin=links[k]['pin_um'];links[k]['distance_um']=abs(pin[0]-(x+w/2))+abs(pin[1]-(y+h/2))
  # Structural predecessor of write-data MIF: preserve exact existing private data stage, co-locate outward.
  if '.u_wd/' in name or '.u_lo_wd/' in name or '.u_hi_wd/' in name:
   dt=next((t for t in i.getITerms() if t.isInputSignal() and t.getMTerm().getName()=='D'),None)
   pred=walk(dt.getNet(),True) if dt else []
   pred=[z for z in pred if ('u_twpd/' in z.getName() or 'u_twd0/' in z.getName() or 'u_twd1/' in z.getName())]
   if len(pred)!=1:conflicts.append(dict(register=name,reason='PRIVATE_WRITE_PREDECESSOR',hits=[z.getName() for z in pred]));continue
   z=pred[0];pn=z.getName();pm=z.getMaster();pw=pm.getWidth()/u;ph=pm.getHeight()/u
   px=x-3*w if side=='W' else x+3*w
   if pn in placements:conflicts.append(dict(register=pn,reason='PRIVATE_MULTIPLE'))
   placements[pn]=dict(x=px,y=y,w=pw,h=ph,bank=bank,side=side,role='private_write',partner=name)
   private.append(dict(private=pn,macro_interface=name,bank=bank,side=side,distance_um=abs(px-x)))
# Canonical exact boundary membership: first capture/last launch, before combinational interior.
pins=json.load(open(root+'/pins.json'));bound=collections.defaultdict(list);boundary_unconnected=[]
for pin in pins:
 pn=pin['bus']+(('['+str(pin['bit'])+']') if pin['bit'] is not None else '')
 if pn=='ck':continue
 bt=b.findBTerm(pn)
 if bt is None:conflicts.append(dict(pin=pn,reason='MISSING_BOUNDARY_PORT'));continue
 back=str(bt.getIoType())=='OUTPUT';hits=walk(bt.getNet(),back)
 if not hits:boundary_unconnected.append(dict(pin=pn,direction=str(bt.getIoType())));continue
 for z in hits:bound[z.getName()].append(dict(pin=pn,x=pin['x'],y=pin['y'],face=pin['face']))
occupied=collections.defaultdict(set);clock_groups=collections.defaultdict(list);boundary_links=[]
for name,pts in sorted(bound.items(),key=lambda kv:(kv[1][0]['face'],sum(v['x']+v['y'] for v in kv[1])/len(kv[1]))):
 if name in placements:conflicts.append(dict(register=name,reason='MACRO_AND_BOUNDARY_CONFLICT'));continue
 faces={v['face'] for v in pts}
 if len(faces)!=1:conflicts.append(dict(register=name,reason='MULTIFACE_BOUNDARY',pins=pts));continue
 face=next(iter(faces));i=b.findInst(name);m=i.getMaster();w=m.getWidth()/u;h=m.getHeight()/u;tx=sum(v['x'] for v in pts)/len(pts);ty=sum(v['y'] for v in pts)/len(pts)
 # Fixed native site lattice; occupancy checked by the actual master bounding box.
 if face=='S':
  candidates=((round(tx/.054)*.054+dx*.054,6.48+dy*.27) for dy in range(48) for dx in range(-80,81))
  group='S'+str(min(3,int(tx/(354.24/4))))
 else:
  candidates=((354.24-6.48-w-dx*.054,round((ty-h/2)/.27)*.27+dy*.27) for dx in range(0,181,math.ceil(w/.054)) for dy in range(-35,36))
  group='EL' if ty<129.6 else 'EH'
 best=None
 for x,y in candidates:
  if not(4.32<=x and x+w<=349.92 and 4.32<=y and y+h<=254.88):continue
  cells={(cx,cy) for cx in range(round(x/.054),math.ceil((x+w-1e-7)/.054)) for cy in range(round(y/.27),math.ceil((y+h-1e-7)/.27))}
  if cells & occupied[face]:continue
  score=abs(x+w/2-tx)+abs(y+h/2-ty)
  if best is None or score<best[0]:best=(score,x,y,cells)
 if best is None:conflicts.append(dict(register=name,reason='BOUNDARY_NO_SITE'));continue
 _,x,y,cells=best;occupied[face]|=cells
 placements[name]=dict(x=x,y=y,w=w,h=h,role='boundary',clock_group=group,face=face)
 clock_groups[group].append(name)
 for pt in pts:boundary_links.append(dict(register=name,**pt,distance_um=abs(x+w/2-pt['x'])+abs(y+h/2-pt['y'])))
# Whole-cell nonoverlap and halo checks (only explicitly proposed IF + private sites).
ps=list(placements.items())
for a,(name,r) in enumerate(ps):
 for n2,r2 in ps[a+1:]:
  if min(r['x']+r['w'],r2['x']+r2['w'])>max(r['x'],r2['x'])+1e-6 and min(r['y']+r['h'],r2['y']+r2['h'])>max(r['y'],r2['y'])+1e-6:overlaps.append([name,n2])
far=[r for r in links if r['distance_um']>20]
counts={str(k):dict(registers=len(v),macro=next(iter(v.values()))['macro']) for k,v in groups.items()}
report=dict(boundary_registers=len(bound),boundary_unconnected=boundary_unconnected,boundary_links=boundary_links,clock_boundary_groups=dict(clock_groups),scope='PROPOSED_WHOLE_CELL_GEOMETRY_FROM_EXACT_SYNTH_CONNECTIVITY_NOT_PNR',source_odb=os.environ['ODB'],profile=p['profile'],pins=len(links),unconnected=exceptions,conflicts=conflicts,over20=far,max_distance_um=max(r['distance_um'] for r in links),private_pairs=len(private),whole_cell_overlaps=overlaps,bank_side_loads=counts,placements=placements,links=links,pairs=private)
json.dump(report,open(root+'/planned_if_sites.json','w'),indent=1)
with open(root+'/planned_if_sites.tcl','w') as f:
 f.write('# Proposed exact-member whole-cell interface placement; apply before placement and remeasure actual F6.\nset b [ord::get_db_block]\nset u [[ord::get_db_tech] getDbUnitsPerMicron]\n')
 for n,r in placements.items():f.write('set i [$b findInst {%s}]; if {$i eq "NULL"} {error {missing planned IF register}}; $i setLocation [expr {round(%s*$u)}] [expr {round(%s*$u)}]; $i setPlacementStatus FIRM\n'%(n,r['x'],r['y']))
print('PLANNED_IF',p['module'],'pins',len(links),'unconnected',len(exceptions),'conflicts',len(conflicts),'far',len(far),'max',report['max_distance_um'],'private',len(private),'overlaps',len(overlaps),'loads',counts,'boundary',len(bound),'boundary_unconnected',len(boundary_unconnected),'boundary_groups',{k:len(v) for k,v in clock_groups.items()})
