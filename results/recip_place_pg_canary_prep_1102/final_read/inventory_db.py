from pathlib import Path
import odb,json,hashlib,gzip,collections,re,os
r=Path('/work');label=os.environ['INVENTORY_LABEL'];base=r/'run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base';name={'SYNTH':'1_synth.odb','FP':'2_floorplan.odb','PLACE':'3_place.odb'}[label];p=base/name;db=odb.read_db(odb.dbDatabase.create(),str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();box=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
d={'label':label,'ODB':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'outline':box(b.getDieArea()),'rows':[{'name':x.getName(),'box':box(x.getBBox()),'orient':str(x.getOrient())} for x in b.getRows()],'instances':{},'masters':{},'pins':[],'PG':{},'classification':'Inventory only; not normal LEC or timing/clock qualification'}
for i in b.getInsts():
 m=i.getMaster();mn=m.getName()
 if mn not in d['masters']:d['masters'][mn]={'count':0,'block':bool(m.isBlock()),'type':str(m.getType()),'mterms':sorted([{'name':t.getName(),'role':str(t.getSigType()),'direction':str(t.getIoType())} for t in m.getMTerms()],key=lambda x:x['name'])}
 d['masters'][mn]['count']+=1
 terms=[];clocks=[]
 for t in i.getITerms():
  mt=t.getMTerm();role=str(mt.getSigType());net=t.getNet();row=[mt.getName(),role,str(mt.getIoType()),net.getName() if net else None]
  if role not in ('POWER','GROUND'):terms.append(row)
  if role=='CLOCK' or mt.getName() in ('CLK','CK','CP'):clocks.append(row)
 d['instances'][i.getName()]={'master':mn,'box':box(i.getBBox()),'orient':str(i.getOrient()),'placement_status':str(i.getPlacementStatus()),'dont_touch':bool(i.isDoNotTouch()),'signal_iterms':sorted(terms),'clock_iterms':sorted(clocks),'sequential_candidate':bool(clocks) or bool(re.search(r'DFF|SDFF|LATCH',mn,re.I))}
for p0 in b.getBTerms():
 for bp in p0.getBPins():
  for z in bp.getBoxes():d['pins'].append({'name':p0.getName(),'dir':str(p0.getIoType()),'signal_type':str(p0.getSigType()),'layer':z.getTechLayer().getName(),'box':box(z)})
for name in ['VDD','VSS']:
 n=b.findNet(name);rects=[]
 if n:
  for sw in n.getSWires():
   for z in sw.getWires():
    if not z.isVia():rects.append({'layer':z.getTechLayer().getName(),'box':box(z)})
 d['PG'][name]={'net_exists':bool(n),'metal_rects':rects,'iterm_count':len(n.getITerms()) if n else 0}
d['summary']={'instances':len(d['instances']),'master_types':len(d['masters']),'placement_status':dict(collections.Counter(x['placement_status'] for x in d['instances'].values())),'sequential_candidates':sum(x['sequential_candidate'] for x in d['instances'].values()),'rows':len(d['rows']),'signal_pin_bits':len({x['name'] for x in d['pins'] if x['signal_type'] not in ('POWER','GROUND')}),'signal_pin_shapes':sum(x['signal_type'] not in ('POWER','GROUND') for x in d['pins'])}
Path('/case/'+label+'_INVENTORY.json.gz').write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode()));print(label,json.dumps(d['summary']))
