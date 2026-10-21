import odb, json, os, hashlib, collections, pathlib
path=os.environ['PG_ODB']; out=os.environ['PG_OUT']
db=odb.dbDatabase.create(); odb.read_db(db,path); b=db.getChip().getBlock()
rows=[]; masters={}; bad=[]; counts=collections.Counter()
for inst in b.getInsts():
 m=inst.getMaster(); terms={t.getMTerm().getName():t for t in inst.getITerms()}
 for mt in m.getMTerms():
  typ=str(mt.getSigType()); pn=mt.getName()
  if typ not in ('POWER','GROUND'):
   if pn.upper() in ('VDD','VSS','VCC','GND','VPWR','VGND'): counts['named_pg_without_native_type']+=1
   continue
  t=terms.get(pn); net=t.getNet() if t else None
  expected='VDD' if typ=='POWER' else 'VSS'
  actual=net.getName() if net else None; nt=str(net.getSigType()) if net else None
  status='PASS' if actual==expected and nt==typ else ('UNBOUND' if net is None else 'WRONG_NET')
  row=[inst.getName(),m.getName(),str(m.getType()),pn,typ,actual,nt,expected,status]
  rows.append(row); counts[status]+=1
  if status!='PASS': bad.append(row)
  masters[m.getName()]=[str(m.getType()),[[x.getName(),str(x.getSigType())] for x in m.getMTerms()]]
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
pathlib.Path(out+'.json').write_text(json.dumps(dict(odb=path,odb_sha256=sha(path),instances=len(b.getInsts()),counts=dict(counts),masters=masters,failures=bad,nets=[[n.getName(),str(n.getSigType()),len(n.getITerms())] for n in b.getNets() if str(n.getSigType()) in ('POWER','GROUND')]),indent=2)+'\n')
with open(out+'.tsv','w') as f:
 f.write('instance\tmaster\tmaster_type\tpin\tpg_type\tactual_net\tnet_type\texpected_net\tstatus\n')
 for r in rows:f.write('\t'.join(str(x) for x in r)+'\n')
print('PG_AUDIT',out,dict(counts))
