import odb,os,re,json,hashlib,collections
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();scale=b.getDbUnitsPerMicron();groups=collections.defaultdict(list)
pat=re.compile(r'^u_core[.]g_safe[.]g_madd\[([0-9]+)\][.]g_fan32[.]u_m[.]genblk1[.]g_native7[.]u_native[.]')
for i in b.getInsts():
 name=i.getName().replace('\\','');m=pat.match(name)
 if m:groups[int(m[1])].append(i)
output=[]
for idx,instances in sorted(groups.items()):
 ids={i.getId() for i in instances};cells=[];internal=[];boundary=[];clock_reset=[];nets={t.getNet().getId():t.getNet() for i in instances for t in i.getITerms() if t.getNet()}
 for i in instances:
  cells.append(dict(name=i.getName(),master=i.getMaster().getName(),dont_touch=i.isDoNotTouch(),ports=sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else '',str(t.getIoType()),str(t.getSigType())) for t in i.getITerms())))
 for n in nets.values():
  pins=list(n.getITerms());sig=str(n.getSigType());reset=bool(re.search('rst|reset',n.getName(),re.I)) or any(re.search(r'^(RESETN?|SETN?|RN|SN|R|S)$',t.getMTerm().getName(),re.I) for t in pins)
  if sig in ('POWER','GROUND','CLOCK') or any(str(t.getSigType())=='CLOCK' for t in pins) or reset:clock_reset.append(n.getName());continue
  row=dict(name=n.getName(),terminals=sorted(t.getInst().getName()+'/'+t.getMTerm().getName() for t in pins),bterms=[t.getName() for t in n.getBTerms()],dont_touch=n.isDoNotTouch())
  if not row['bterms'] and all(t.getInst().getId() in ids for t in pins):internal.append(row)
  else:boundary.append(row)
 cells.sort(key=lambda x:x['name']);internal.sort(key=lambda x:x['name']);boundary.sort(key=lambda x:x['name']);area=sum(i.getMaster().getWidth()*i.getMaster().getHeight()/scale**2 for i in instances)
 output.append(dict(index=idx,cells=cells,cell_count=len(cells),cell_area_um2=area,master_counts=dict(collections.Counter(i.getMaster().getName() for i in instances)),internal_data_nets=internal,boundary_data_nets=boundary,clock_reset_pg_nets=sorted(clock_reset),cell_port_identity_sha256=hashlib.sha256(json.dumps(cells,sort_keys=True).encode()).hexdigest()))
out=dict(schema='opentallas.frozen_kernel_inventory.v1',odb=str(p),odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),groups=output)
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(out,indent=2)+'\n');print([(g['index'],g['cell_count'],round(g['cell_area_um2'],3),len(g['internal_data_nets']),len(g['boundary_data_nets'])) for g in output])
