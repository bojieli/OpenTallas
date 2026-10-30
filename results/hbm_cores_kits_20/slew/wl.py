import odb,sys,collections
db=odb.read_db(odb.dbDatabase.create(),sys.argv[1]);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
names=[l.strip() for l in open(sys.argv[2]) if l.strip()]
out=open(sys.argv[3],'w')
for nn in names:
  n=b.findNet(nn)
  if n is None: continue
  # guides
  gl=collections.Counter()
  for g in n.getGuides():
    bx=g.getBox(); L=g.getLayer().getName(); gl[L]+=max(bx.dx(),bx.dy())/u
  rl=collections.Counter(); vias=0
  w=n.getWire()
  if w:
    dec=odb.dbWireDecoder(); dec.begin(w); layer=None; last=None
    while True:
      op=dec.next()
      if op==odb.dbWireDecoder.END_DECODE: break
      if op in (odb.dbWireDecoder.PATH,odb.dbWireDecoder.JUNCTION,odb.dbWireDecoder.SHORT,odb.dbWireDecoder.VWIRE):
        layer=dec.getLayer().getName(); last=None
      elif op in (odb.dbWireDecoder.POINT,odb.dbWireDecoder.POINT_EXT):
        p=dec.getPoint()[:2]
        if last is not None: rl[layer]+=(abs(p[0]-last[0])+abs(p[1]-last[1]))/u
        last=p
      elif op in (odb.dbWireDecoder.VIA,odb.dbWireDecoder.TECH_VIA):
        vias+=1; layer=None
        try: layer=(dec.getVia() if op==odb.dbWireDecoder.VIA else dec.getTechVia()).getTopLayer().getName()
        except Exception: pass
  out.write("%s\t%.1f\t%.1f\t%d\t%s\t%s\n"%(nn,sum(gl.values()),sum(rl.values()),vias,dict(gl),{k:round(v,1) for k,v in rl.items()}))
