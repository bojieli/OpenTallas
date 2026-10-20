import odb,json,sys
from pathlib import Path
src,rolesp,out=map(Path,sys.argv[1:4]);db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();roles=json.loads(rolesp.read_text())['master_roles']
rows=[]
def drivers(n):
 return [p for p in n.getITerms()if str(p.getMTerm().getIoType())=='OUTPUT'] if n else []
def walk(i,depth,seen):
 name=i.getName();typ=i.getMaster().getName();pins=roles.get(typ,{}).get('pins',{})
 if any(z.get('clock')for z in pins.values()):return {name}
 if depth<=0:return {'DEPTH:'+name}
 if name in seen:return {'LOOP:'+name}
 seen=seen|{name};out=set()
 for p in i.getITerms():
  if str(p.getMTerm().getIoType())!='INPUT' or str(p.getMTerm().getSigType())in['POWER','GROUND']:continue
  n=p.getNet()
  for q in drivers(n):out.update(walk(q.getInst(),depth-(not roles.get(typ,{}).get('unary',False)),seen))
 return out
for name in ['_281620_','_207181_','_219344_','_219349_','_219663_','_222334_','_226897_','_219668_']:
 i=b.findInst(name)
 if not i:continue
 rows.append({'driver':name,'master':i.getMaster().getName(),'ports':{p.getMTerm().getName():p.getNet().getName()if p.getNet()else None for p in i.getITerms()if str(p.getMTerm().getSigType())not in['POWER','GROUND']},'upstream_registers_or_depth8':sorted(walk(i,8,set()))})
out.write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
