"""Read actual post-PLACE ODB once, guard protected geometry and export for native LOOK/census. No mutation."""
import os,json,collections
from pathlib import Path
import odb
db=odb.dbDatabase.create();odb.read_db(db,os.environ['ODB']);block=db.getChip().getBlock();u=block.getDbUnitsPerMicron();assert u==1000
W=Path('/work');T=json.load(open(W/'targets_actualFP.json'))['targets'];base=json.load(open(W/'protected_FP.json'));norm=lambda n:n.replace('\\','');targets={x['name']:x for x in T};seen=set();ff=[];errors=[]
def rect(b):return[b.xMin(),b.yMin(),b.xMax(),b.yMax()]
cb=block.findBTerm('ck');assert cb and cb.getNet(), 'actual scalar ck BTerm/net missing'
clocknets=set();todo=[cb.getNet()]
while todo:
 n=todo.pop()
 if n.getName()in clocknets:continue
 clocknets.add(n.getName())
 for q in n.getITerms():
  if q.isOutputSignal():continue
  i=q.getInst();m=i.getMaster().getName();pin=q.getMTerm().getName()
  if m.startswith(('BUF','INV','CKBUF','CKINV','HB'))or(m.startswith('ICG')and pin in('CLK','CK')):
   todo.extend(t.getNet()for t in i.getITerms()if t.isOutputSignal()and t.getNet())
fixed={norm(r['name']):r for r in base['fixed']};fixed_seen=set();taps=0;macro=0;bay=[321840,328320,326160,332640];intrude=[]
for i in block.getInsts():
 n=norm(i.getName());m=i.getMaster();b=rect(i.getBBox());status=str(i.getPlacementStatus())
 if m.getName().startswith('TAPCELL'):taps+=1
 if m.isBlock():macro+=1
 if i.isPlaced()and b[0]<bay[2]and b[2]>bay[0]and b[1]<bay[3]and b[3]>bay[1]:intrude.append(n)
 if n in targets:
  t=targets[n];x,y=[round(z*u)for z in t['origin_um']];w,h=[round(z*u)for z in t['size_um']];want=[x,y,x+w,y+h]
  if n in seen:errors.append(['duplicateFF',n])
  clock_driver=any(q.isOutputSignal()and q.getNet()and q.getNet().getName()in clocknets for q in i.getITerms())
  if m.getName()!=t['master']or b!=want or str(i.getOrient())!=t['row_orient']or status!='FIRM'or bool(i.isDoNotTouch())!=clock_driver:errors.append(['FFchanged',n,m.getName(),b,str(i.getOrient()),status,i.isDoNotTouch()])
  seen.add(n);ff.append(dict(name=i.getName(),master=m.getName(),bbox_dbu=b,orient=str(i.getOrient()),status=status,dont_touch=i.isDoNotTouch()))
 if n in fixed:
  r=fixed[n]
  if m.getName()!=r['master']or b!=r['bbox_dbu']or str(i.getOrient())!=r['orient']:errors.append(['fixedTAPmacrochanged',n])
  fixed_seen.add(n)
if len(seen)!=31847:errors.append(['FFcardinality',len(seen)])
if len(fixed_seen)!=len(fixed)or taps!=36809 or macro!=32:errors.append(['fixedcardinality',len(fixed_seen),len(fixed),taps,macro])
totalFF=sum(i.getMaster().getName().startswith(('DFFHQN','DFFASRHQN'))for i in block.getInsts())
if totalFF!=31847:errors.append(['FFcloned',totalFF])
if intrude:errors.append(['clockbayintrusion',intrude])
nb=sum(rect(k.getBBox())==bay for k in block.getBlockages())
if nb!=1:errors.append(['clockbayblockage',nb])
snapshot=dict(dbu_per_um=u,rows=[dict(name=r.getName(),bbox_dbu=rect(r.getBBox()),origin=list(r.getOrigin()),orient=str(r.getOrient()))for r in block.getRows()],fixed=[],macros=[],controls=[],PG_rects=[])
for i in block.getInsts():
 n=norm(i.getName());m=i.getMaster();st=str(i.getPlacementStatus())
 if n in fixed:snapshot['fixed'].append(dict(name=i.getName(),master=m.getName(),bbox_dbu=rect(i.getBBox()),orient=str(i.getOrient()),status=st))
 if m.isBlock():snapshot['macros'].append(dict(name=i.getName(),master=m.getName(),bbox_dbu=rect(i.getBBox()),orient=str(i.getOrient())))
for bt in block.getBTerms():
 if bt.getName()in('ck','rst'):snapshot['controls'].append(dict(name=bt.getName(),boxes=[dict(layer=b.getTechLayer().getName(),bbox_dbu=rect(b))for bp in bt.getBPins()for b in bp.getBoxes()if b.getTechLayer()]))
for n in block.getNets():
 if str(n.getSigType())not in('POWER','GROUND'):continue
 for wire in n.getSWires():
  for b in wire.getWires():
   if not b.isVia()and b.getTechLayer()and b.getTechLayer().getName()in('M5','M6'):snapshot['PG_rects'].append(dict(net=n.getName(),layer=b.getTechLayer().getName(),bbox_dbu=rect(b)))
rowkey=lambda rs:sorted((tuple(r['bbox_dbu']),tuple(r['origin']),r['orient'])for r in rs)
if rowkey(snapshot['rows'])!=rowkey(base['rows']):errors.append(['rowinventorychanged'])
pgkey=lambda rows:sorted((r['net'],r['layer'],tuple(r['bbox_dbu']))for r in rows)
if pgkey(snapshot['PG_rects'])!=pgkey(base['PG_rects']):errors.append(['PGwiregeometrychanged'])
(W/'post_place_snapshot.json').write_text(json.dumps(snapshot));(W/'post_place_FF.json').write_text(json.dumps(ff));(W/'protected_guard.json').write_text(json.dumps(dict(FF=totalFF,FF_exact=len(seen),TAP=taps,macros=macro,fixed_exact=len(fixed_seen),clock_bay_cells=len(intrude),errors=errors),indent=2))
output=W/'post_place.odb';exec(compile((W/'export_native_geom.py').read_text(),'/work/export_native_geom.py','exec'))
# Same unchanged platform tracks/master obstructions for placed cut/RUDY analysis, not old measurements.
with(W/'actual_geom.tsv').open('a')as f:f.write((W/'geom_tech.tsv').read_text())
print('POST_PLACE protected guard',len(errors),'errors',totalFF,'FF',taps,'TAP',macro,'macros')
assert not errors,errors[:8]
