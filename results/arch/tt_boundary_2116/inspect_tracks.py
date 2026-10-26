exec(open('/audit.py').read().split("out={'dbu'")[0])
for l in db.getTech().getLayers():
 if l.getRoutingLevel():
  g=b.findTrackGrid(l);print(l.getName(),l.getDirection(), 'X',[g.getGridPatternX(i) for i in range(g.getNumGridPatternsX())] if g else None,'Y',[g.getGridPatternY(i) for i in range(g.getNumGridPatternsY())] if g else None)
miss={};n={}
for t in b.getBTerms():
 if t.getSigType() in ['POWER','GROUND']:continue
 for bp in t.getBPins():
  for bx in bp.getBoxes():
   ln=bx.getTechLayer().getName();axis='x' if ln=='M5' else 'y'
   c=(bx.xMin()+bx.xMax())/2 if axis=='x' else (bx.yMin()+bx.yMax())/2
   n[ln]=n.get(ln,0)+1
   if ln in ['M4','M5'] and (c-12)%48:miss.setdefault(ln,[]).append({'name':t.getName(),'center_dbu':c,'axis':axis,'residual_dbu':(c-12)%48})
print('COUNTS',n, {k:len(v) for k,v in miss.items()});print('EXAMPLES',{k:v[:5] for k,v in miss.items()})
