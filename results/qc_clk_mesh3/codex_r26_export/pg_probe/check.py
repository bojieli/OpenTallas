import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'/w/encoded.odb');b=D.getChip().getBlock();dbu=b.getDbUnitsPerMicron();lower=b.findInst('ckt_0_0');upper=b.findInst('ckt_0_1');upper.setPlacementStatus('PLACED');lower.setPlacementStatus('PLACED');upper.swapMaster(lower.getMaster())
master=lower.getMaster();height=master.getHeight();rails={}
for name in ['VDD','VSS']:
 t=master.findMTerm(name);rails[name]=[g for g in t.getMPins()[0].getGeometry() if g.getTechLayer().getName()=='M1']
def world(inst):
 out={};bb=inst.getBBox();x0,y0=bb.xMin(),bb.yMin();mx=str(inst.getOrient())=='MX'
 for name,rs in rails.items():
  out[name]=[]
  for r in rs:
   ya,yb=(height-r.yMax(),height-r.yMin()) if mx else (r.yMin(),r.yMax())
   out[name].append([x0+r.xMin(),y0+ya,x0+r.xMax(),y0+yb])
 return out
def overlap(a,c):return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]
lower.setOrient('R0');lower.setLocation(10800,10800);upper.setOrient('R0');upper.setLocation(10800,10800+height)
a=world(lower);wrong=world(upper)
assert any(overlap(x,y) for x in a['VDD'] for y in wrong['VSS'])
upper.setOrient('MX');upper.setLocation(10800,10800+height);good=world(upper)
assert any(overlap(x,y) for x in a['VDD'] for y in good['VDD'])
assert not any(overlap(x,y) for n in ['VDD','VSS'] for m in ['VDD','VSS'] if n!=m for x in a[n] for y in good[m])
r=dict(verdict='PASS',master=master.getName(),dbu_per_um=dbu,height_dbu=height,lower_R0=a,wrong_upper_R0=wrong,correct_upper_MX=good,proof='Actual native M1 PG boxes: R0/R0 opposite-net overlap; R0/MX same-net abutment with no opposite-net overlap')
open('/w/result.json','w').write(json.dumps(r,indent=1));odb.write_db(D,'/w/oriented.odb');print(json.dumps(r))
