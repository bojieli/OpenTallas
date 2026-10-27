import odb,json,collections
expected=json.load(open('/w/expected.json'));results={}
for name,item in expected.items():
 db=odb.dbDatabase.create();odb.read_db(db,'/w/'+name+'.odb');b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
 n=b.findNet('root');w=n.getWire();assert w is not None
 vias=[];metal=[];it=odb.dbWirePathItr();it.begin(w);pa=odb.dbWirePath();ps=odb.dbWirePathShape()
 while it.getNextPath(pa):
  while it.getNextShape(ps):
   sh=ps.shape
   if sh.isVia():
    v=sh.getTechVia();assert v is not None
    x,y=sh.getViaXY();vias.append((v.getName(),round(x/u,6),round(y/u,6)))
   else:metal.append((sh.getTechLayer().getName(),sh.xMin()/u,sh.yMin()/u,sh.xMax()/u,sh.yMax()/u))
 wanted=[]
 for a,z in item['graph']['edges']:
  if a[0]!=z[0]:
   k=min(int(a[0][1:]),int(z[0][1:]));wanted.append(('VIA'+str(k)+str(k+1),a[1],a[2]))
  else:
   assert any(layer==a[0] and x0<=min(a[1],z[1]) and x1>=max(a[1],z[1]) and y0<=min(a[2],z[2]) and y1>=max(a[2],z[2]) for layer,x0,y0,x1,y1 in metal),(name,a,z,metal)
 assert collections.Counter(vias)==collections.Counter(wanted),(name,vias,wanted)
 pins={}
 for term in item['graph']['taps']:
  bt=b.findBTerm(term['port']);assert bt.getNet()==n
  at=term['port_node'];boxes=[box for bp in bt.getBPins() for box in bp.getBoxes()]
  assert any(box.getTechLayer().getName()==at[0] and box.xMin()/u<=at[1]<=box.xMax()/u and box.yMin()/u<=at[2]<=box.yMax()/u for box in boxes),(name,at)
  pins[term['port']]=at
 results[name]=dict(verdict='PASS',native_vias=vias,expected_via_count=len(wanted),pins=pins,metal_shapes=len(metal))
open('/w/result.json','w').write(json.dumps(results,indent=1));print('NATIVE_VIA_COUPON_PASS',json.dumps(results))
