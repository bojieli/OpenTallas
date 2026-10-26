import odb,os,collections,re,json
D=odb.dbDatabase.create();odb.read_db(D,os.environ['ODB']);b=D.getChip().getBlock();u=b.getDbUnitsPerMicron();rows=[]
def ff(m):return any(x in m.getName() for x in ('DFF','DHL','SDF'))
for i in b.getInsts():
 if not i.getMaster().isBlock():continue
 for t in i.getITerms():
  p=t.getMTerm().getName()
  if not t.isInputSignal() or not re.match(r'^(r_ce_in|r_addr_in|w_ce_in|w_addr_in|wd_in)(\[|$)',p):continue
  ok,x,y=t.getAvgXY();q=collections.deque([(t.getNet(),0,0)]);seen={};hits=[]
  while q:
   n,logic,buffs=q.popleft()
   if n is None:continue
   key=n.getName()
   if key in seen and seen[key]<=logic:continue
   seen[key]=logic
   for z in n.getITerms():
    if not z.isOutputSignal():continue
    c=z.getInst();m=c.getMaster()
    if m.isBlock():continue
    if ff(m):
     a,d=c.getLocation();hits.append(((abs(a-x)+abs(d-y))/u,c.getName(),logic,buffs));continue
    buf=bool(re.match(r'^(BUF|INV|HB)',m.getName()));cost=logic+(not buf)
    if cost>4:continue
    for it in c.getITerms():
     if it.isInputSignal() and it.getMTerm().getSigType()=='SIGNAL':q.append((it.getNet(),cost,buffs+buf))
  hit=min(hits) if hits else None
  rows.append(dict(macro=i.getName(),pin=p,distance_um=hit[0] if hit else None,register=hit[1] if hit else None,logic_depth=hit[2] if hit else None,buffers=hit[3] if hit else None))
missing=[r for r in rows if r['distance_um'] is None];far=[r for r in rows if r['distance_um'] is not None and r['distance_um']>20]
with open('/work/f6_full_inputs.json','w') as f:json.dump(dict(verdict='PASS' if not missing and not far else 'FAIL',pins=len(rows),missing=missing,over20=far,rows=rows),f,indent=1)
print('F6_FULL_INPUTS',len(rows),'missing',len(missing),'over20',len(far),'max',max(r['distance_um'] or 0 for r in rows))
for r in rows:
 if (r['buffers'] or 0)>3:print('F6_BUFFER_CHAIN',r)
