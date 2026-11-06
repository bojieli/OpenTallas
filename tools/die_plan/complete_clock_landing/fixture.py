"""Private geometry fixture: retain all physical instances/PG, route real drivers to outside waypoints."""
import odb,json,os
landing={}
for line in open('/out/landing_plan.tsv'):
 name,px,py,x,y=line.rstrip('\n').split('\t');landing[name]=tuple(map(int,(px,py,x,y)))
expected=int(os.environ['OT_LANDING_COUNT']);master=os.environ['OT_LANDING_MASTER']
assert len(landing)==expected
source=os.environ['IN']
d=odb.dbDatabase.create();odb.read_db(d,source);b=d.getChip().getBlock();nets=[];drivers=set();receivers=[]
for i in b.getInsts():
 if i.getMaster().getName()==master:
  t=i.findITerm('clk');n=t.getNet();ts=list(n.getITerms());assert len(ts)==2 and str(n.getSigType())=='CLOCK'
  other=next(z for z in ts if z!=t);assert str(other.getIoType())=='OUTPUT' and not other.getInst().getMaster().isBlock()
  nets.append(n);drivers.add(other.getInst().getName());receivers.append(i.getName())
assert len(nets)==expected and {n.getName() for n in nets}==set(landing)
keep={n.getName() for n in nets}
# Private geometry fixture only: disconnecting other clocks requires clearing
# dont-touch metadata; every placement/orientation remains unchanged.
for i in b.getInsts():i.setDoNotTouch(False)
for n in list(b.getNets()):
 if n.getName() not in keep and str(n.getSigType()) not in ('POWER','GROUND'):
  n.setDoNotTouch(False);odb.dbNet.destroy(n)
# Preserve EVERY placed cell as a real routing obstruction, including nearby pins.
for t in list(b.getBTerms()):
 if str(t.getSigType()) not in ('POWER','GROUND'):odb.dbBTerm.destroy(t)
for index,n in enumerate(nets):
 receiver=next(t for t in n.getITerms() if t.getInst().getMaster().isBlock())
 receiver.disconnect()
 px,py,x,y=landing[n.getName()]
 terminal=odb.dbBTerm.create(n,'__ot_land_'+str(index));terminal.setIoType('OUTPUT');terminal.setSigType('CLOCK')
 pin=odb.dbBPin.create(terminal);pin.setPlacementStatus('FIRM');w=d.getTech().findLayer('M5').getWidth()
 odb.dbBox.create(pin,d.getTech().findLayer('M5'),x-w//2,y-w//2,x+w//2,y+w//2)
 if n.getWire():odb.dbWire.destroy(n.getWire())
 # Discard old guides; this fixture routes every complete leaf natively.
 for g in list(n.getGuides()):odb.dbGuide.destroy(g)
odb.write_db(d,'/out/clock_leaf_fixture.odb')
u=b.getDbUnitsPerMicron();r=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
a={'dbu':u,'core':r(b.getCoreArea()),'macros':[],'drivers':[],'ports':[],'landings':[list(q) for q in landing.values()]}
for i in b.getInsts():
 if i.getMaster().isBlock():a['macros'].append([i.getName(),r(i.getBBox())])
 elif i.getName() in drivers:a['drivers'].append([i.getName(),r(i.getBBox())])
for n in nets:
 for t in n.getITerms():
  for l,q in t.getGeometries():a['ports'].append([t.getInst().getName(),l.getName(),r(q)])
open('/out/fixture_geom.json','w').write(json.dumps(a))
print('FIXTURE',len(nets),'CLOCK leaves; preserve all macro/PG geometry; native real drivers',sorted(drivers))
