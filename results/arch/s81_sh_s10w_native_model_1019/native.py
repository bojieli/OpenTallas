import odb,json,hashlib,collections,math
P='/frozen/routes/gate/work/orfs/results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/5_1_grt.odb'
db=odb.dbDatabase.create(); odb.read_db(db,P); b=db.getChip().getBlock(); U=b.getDbUnitsPerMicron()
def ident(p):
 return p.getInst().getName()+'/'+p.getMTerm().getName() if hasattr(p,'getInst') else 'PORT/'+p.getName()
def xy(p):
 if hasattr(p,'getInst'):
  v=p.getAvgXY(); return (v[1]/U,v[2]/U) if v[0] else None
 ps=[r for bp in p.getBPins() for r in bp.getBoxes()]
 return ((ps[0].xMin()+ps[0].xMax())/2/U,(ps[0].yMin()+ps[0].yMax())/2/U) if ps else None
def typ(p):
 if not hasattr(p,'getInst'): return 'input'
 m=p.getInst().getMaster().getName()
 return 'FF' if m.startswith('DFF') else 'tie' if m.startswith('TIE') else 'macro' if p.getInst().getMaster().isBlock() else 'comb'
def buffer(i): return i.getMaster().getName().startswith(('BUF','INV'))
def pg(p): return p.getSigType() in ('POWER','GROUND')
drivers=[]; nets={}; macros=[]; counts=collections.Counter()
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND','CLOCK'): continue
 ds=[p for p in n.getITerms() if not pg(p) and p.getIoType()=='OUTPUT']+[p for p in n.getBTerms() if p.getIoType()=='INPUT']
 ss=[p for p in n.getITerms() if not pg(p) and p.getIoType()=='INPUT']+[p for p in n.getBTerms() if p.getIoType()=='OUTPUT']
 nets[n.getName()]=(ds,ss)
 for p in ds:
  if hasattr(p,'getInst') and buffer(p.getInst()): continue
  if ident(p)=='PORT/ck': continue
  drivers.append(p)
def endpoints(p):
 out=[]; seen=set(); stack=[p.getNet()]
 while stack:
  n=stack.pop()
  if not n or n.getName() in seen: continue
  seen.add(n.getName())
  for s in nets.get(n.getName(),([],[]))[1]:
   if hasattr(s,'getInst') and buffer(s.getInst()):
    stack.extend(t.getNet() for t in s.getInst().getITerms() if t.getIoType()=='OUTPUT')
   else: out.append(s)
 return out
unsafe=[]; far=[]; pin_bad=[]; output_bad=[]; maxima=collections.defaultdict(int)
for p in drivers:
 es=endpoints(p); t=typ(p); counts[t]+=1; maxima[t]=max(maxima[t],len(es)); pos=xy(p)
 row={'driver':ident(p),'type':t,'loads':len(es),'master':p.getInst().getMaster().getName() if hasattr(p,'getInst') else None}
 if len(es)>32: unsafe.append(dict(row,endpoints=[ident(s) for s in es]))
 for s in es:
  q=xy(s)
  if not hasattr(s,'getInst') and t!='FF': output_bad.append({'output':ident(s),'driver':ident(p),'driver_type':t})
  if pos and q:
   dist=abs(pos[0]-q[0])+abs(pos[1]-q[1])
   if dist>405: far.append({'driver':ident(p),'sink':ident(s),'manhattan_um':dist,'type':t})
  if t=='input' and ident(p) not in ('PORT/rst_n',) and typ(s)!='FF': pin_bad.append({'input':ident(p),'first_sink':ident(s),'sink_type':typ(s)})
for i in b.getInsts():
 m=i.getMaster()
 if not m.isBlock(): continue
 pins=[]; pgs=[]
 for mt in m.getMTerms():
  rects=[{'layer':g.getTechLayer().getName(),'box':[g.xMin()/U,g.yMin()/U,g.xMax()/U,g.yMax()/U]} for mp in mt.getMPins() for g in mp.getGeometry() if g.getTechLayer()]
  it=i.findITerm(mt.getName())
  r={'name':mt.getName(),'type':mt.getSigType(),'net':it.getNet().getName() if it and it.getNet() else None,'rects':rects}
  (pgs if mt.getSigType() in ('POWER','GROUND') else pins).append(r)
 macros.append({'inst':i.getName(),'master':m.getName(),'width':m.getWidth()/U,'height':m.getHeight()/U,'origin':i.getOrigin(),'orient':i.getOrient(),'pins':pins,'pg_mterm_universe':pgs})
out={'output_non_ff':output_bad,'cell_area_um2':sum(i.getMaster().getWidth()*i.getMaster().getHeight()/U/U for i in b.getInsts() if not i.getMaster().isBlock()),'ff_master_areas':{i.getMaster().getName():i.getMaster().getWidth()*i.getMaster().getHeight()/U/U for i in b.getInsts() if i.getMaster().getName().startswith('DFF')},'stage':'GRT diagnostic only','odb_sha256':hashlib.sha256(open(P,'rb').read()).hexdigest(),'instances':len(b.getInsts()),'drivers':dict(counts),'max_loads':dict(maxima),'unsafe':unsafe,'far_pairs':far,'input_non_ff':pin_bad,'macros':macros,'undriven_nets':[k for k,(d,s) in nets.items() if s and not d],'multidriven_nets':[k for k,(d,s) in nets.items() if len(d)>1]}
open('/out/native.json','w').write(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ('unsafe','far_pairs','input_non_ff','macros','undriven_nets','multidriven_nets')},indent=2)); print('UNSAFE',len(unsafe),'FAR',len(far),'INPUT_NON_FF',len(pin_bad),'MACROS',len(macros)); print('PG',[(x['master'],[(p['name'],p['net'],len(p['rects'])) for p in x['pg_mterm_universe']]) for x in macros])
