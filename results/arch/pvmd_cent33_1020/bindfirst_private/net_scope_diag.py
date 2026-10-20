import odb,re,json,collections,os
from pathlib import Path
p=Path('/original/1_synth.odb');db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();groups=collections.defaultdict(list)
pat=re.compile(r'^u_core[.]g_safe[.]g_madd\[([0-9]+)\][.]g_fan32[.]u_m[.]genblk1[.]g_native7[.]u_native[.]')
for i in b.getInsts():
 m=pat.match(i.getName().replace('\\',''))
 if m:groups[int(m[1])].append(i)
out=[]
for idx,insts in sorted(groups.items()):
 ids={i.getId() for i in insts};nets={t.getNet().getId():t.getNet() for i in insts for t in i.getITerms() if t.getNet()};counts=collections.Counter();examples=collections.defaultdict(list)
 for n in nets.values():
  terms=list(n.getITerms());sig=str(n.getSigType())
  if sig in ('POWER','GROUND','CLOCK') or list(n.getBTerms()) or not all(t.getInst().getId() in ids for t in terms):continue
  reset=bool(re.search('rst|reset',n.getName(),re.I)) or any(re.search(r'^(RESETN?|SETN?|RN|SN|R|S)$',t.getMTerm().getName(),re.I) for t in terms)
  if reset or any(str(t.getSigType())=='CLOCK' for t in terms):continue
  drivers=sum(str(t.getIoType())=='OUTPUT' for t in terms);loads=sum(str(t.getIoType())=='INPUT' for t in terms)
  reason=('driver_'+str(drivers)+'_loads_'+str(loads)) if drivers!=1 or loads==0 else 'one_driver_with_loads'
  counts[reason]+=1
  if len(examples[reason])<4:examples[reason].append(dict(net=n.getName(),terms=[(t.getInst().getName(),t.getInst().getMaster().getName(),t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType())) for t in terms]))
 out.append(dict(lane=idx,counts=dict(counts),examples=dict(examples)))
Path('/work/net_scope_diag.json').write_text(json.dumps(out,indent=2)+'\n');print([(x['lane'],x['counts']) for x in out])
