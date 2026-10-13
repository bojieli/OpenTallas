import odb,json,collections
D=odb.dbDatabase.create();odb.read_db(D,'/work/region.odb');b=D.getChip().getBlock()
obs=collections.defaultdict(list)
for o in b.getObstructions():
 r=o.getBBox();obs[r.getTechLayer().getName()].append((r.xMin(),r.yMin(),r.xMax(),r.yMax()))
c=collections.Counter();ex=[]
for t in b.getBTerms():
 if '__drdp' not in t.getName():continue
 for p in t.getBPins():
  for g in p.getBoxes():
   ln=g.getTechLayer().getName();up='M'+str(int(ln[1:])+1) if ln.startswith('M') else ''
   c['pins']+=1
   r=(g.xMin(),g.yMin(),g.xMax(),g.yMax())
   blockers=[q for q in obs.get(up,[]) if q[0]<=r[0] and q[2]>=r[2] and q[1]<=r[1] and q[3]>=r[3]]
   if blockers:
    c['above_blocked_obs']+=1;c[ln+'->'+up]+=1
    if len(ex)<12:ex.append({'terminal':t.getName(),'layer':ln,'above':up,'pin_box':r,'obs_boxes':blockers[:2]})
print(json.dumps({'counts':dict(c),'examples':ex,'scope':'Exact intruder terminal geometry in retained ioedge2 region.odb; block OBS only, PDN not counted'}))
