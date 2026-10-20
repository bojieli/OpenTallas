import csv,collections,json,gzip,hashlib,pathlib
p=pathlib.Path('.')
counts=collections.Counter(); masters=collections.Counter(); failures=[]; missing=collections.Counter(); statuses=collections.Counter()
for r in csv.DictReader(open('native_pg.tsv'),delimiter='\t'):
 counts[(r['role'],r['expected_net'],r['actual_net'],r['status'].split()[0],r['protected'])]+=1
 statuses[r['status'].split()[0]]+=1
 if r['status']!='PASS':
  masters[r['master']]+=1
  if len(failures)<20 or (r['protected']=='1' and len(failures)<40):failures.append(r)
report={'verdict':'PG_HOLD','counts':[dict(zip(['role','expected_net','actual_net','status','protected'],k),count=v) for k,v in sorted(counts.items())],'statuses':dict(statuses),'failure_by_master':dict(masters),'samples':failures,'physical_contact_connectivity':'OPEN: logical binding census does not prove pin shape/contact connectivity','files':{}}
for name in ['native_pg.tsv','master_pg.tsv','global_rules.tsv','odb.sha256','image.txt','audit.tcl','native_pg_binding.tcl']:
 report['files'][name]=hashlib.sha256(p.joinpath(name).read_bytes()).hexdigest()
for name in ['native_pg.tsv','master_pg.tsv']:
 with open(name,'rb') as src,gzip.open(name+'.gz','wb') as dst:
  import shutil;shutil.copyfileobj(src,dst)
pathlib.Path('summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'statuses':dict(statuses),'protected_failure_pins':sum(v for k,v in counts.items() if k[-1]=='1' and k[-2]!='PASS')}))
