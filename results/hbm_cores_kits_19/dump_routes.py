import pathlib,json,odb
for label,nick in [('ring','hbc_ot_hfd_coll_q2_hard_v8g__ring_ag'),('bd','hbc_ot_hgi_sm_xload_cl2_bdring')]:
 p=pathlib.Path('/'+label);db=odb.read_db(odb.dbDatabase.create(),str(p/'run/results/asap7'/nick/'base/6_final.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();imap={i.getName().replace('\\',''):i for i in b.getInsts()}
 def cell(i):
  x,y=i.getLocation();m=i.getMaster();return {'name':i.getName(),'master':m.getName(),'x':x/u,'y':y/u,'w':m.getWidth()/u,'h':m.getHeight()/u}
 points=[cell(i) for i in b.getInsts() if not any(i.getMaster().getName().startswith(s) for s in ['FILLER','DECAP','TAPCELL'])];nets={}
 for line in pathlib.Path('/work/'+label+'_viol.txt').read_text().splitlines():
  cn,pin=line.rsplit('/',1);i=imap.get(cn)
  if i is None:continue
  t=i.findITerm(pin)
  if t is None:continue
  n=t.getNet()
  if n.getName() not in nets:
   nets[n.getName()]={'name':n.getName(),'drivers':[{'cell':cell(t.getInst()),'pin':t.getMTerm().getName()} for t in n.getITerms() if t.getIoType()=='OUTPUT'],'loads':[{'cell':cell(t.getInst()),'pin':t.getMTerm().getName()} for t in n.getITerms() if t.getIoType()=='INPUT'],'violations':0}
  nets[n.getName()]['violations']+=1
 pathlib.Path('/work/'+label+'_routes.json').write_text(json.dumps({'points':points,'nets':list(nets.values())}));print('DUMP',label,'points',len(points),'violnets',len(nets),flush=True)
