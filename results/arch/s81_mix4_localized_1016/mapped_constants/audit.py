import odb,json,hashlib,re,gzip
from pathlib import Path
W=Path('/work');manifest=json.loads((W/'manifest.json').read_text());functions={};lib_evidence={}
def constant(cell,pin):
 if(cell,pin)in functions:return functions[(cell,pin)]
 for lib in Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*RVT_TT*'):
  raw=lib.read_bytes();s=gzip.decompress(raw).decode()if lib.suffix=='.gz'else raw.decode();m=re.search(r'\bcell\s*\(\s*"?'+re.escape(cell)+r'"?\s*\)\s*\{',s)
  if not m:continue
  start=m.end();depth=1;end=start
  while depth and end<len(s):depth+=(s[end]=='{')-(s[end]=='}');end+=1
  block=s[start:end];pm=re.search(r'\bpin\s*\(\s*"?'+re.escape(pin)+r'"?\s*\)\s*\{',block)
  if not pm:continue
  ps=pm.end();dep=1;pe=ps
  while dep and pe<len(block):dep+=(block[pe]=='{')-(block[pe]=='}');pe+=1
  f=re.search(r'\bfunction\s*:\s*"([^"]+)"',block[ps:pe]);expr=f[1].strip()if f else None
  if expr in ('0','1'):
   v=int(expr);functions[(cell,pin)]=v;lib_evidence[cell+'.'+pin]={'lib':str(lib),'lib_sha256':hashlib.sha256(raw).hexdigest(),'cell':cell,'output_pin':pin,'function':expr};return v
 return None
results=[]
for item in manifest['cells']:
 path=Path(item['odb']);db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock();rows=[]
 for pin in item['pins']:
  bt=block.findBTerm(pin);drivers=[]
  if bt and bt.getNet():
   for it in bt.getNet().getITerms():
    if str(it.getMTerm().getIoType())in ('OUTPUT','INOUT'):
     master=it.getInst().getMaster();term=it.getMTerm();drivers.append({'inst':it.getInst().getName(),'master':master.getName(),'master_type':str(master.getType()),'pin':term.getName(),'constant_lib_function':constant(master.getName(),term.getName())})
  value=drivers[0]['constant_lib_function']if len(drivers)==1 else None;rows.append({'port':pin,'net':bt.getNet().getName()if bt and bt.getNet()else None,'drivers':drivers,'constant_zero_proved':value==0})
 r={**item,'odb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'actual_block':block.getName(),'rows':rows,'proved':sum(row['constant_zero_proved']for row in rows),'expected':len(item['pins'])};results.append(r);odb.dbDatabase.destroy(db)
report={'status':'ACTUAL_ODB_AND_LIBERTY_CONSTANT_DRIVER_PROOF'if all(r['proved']==r['expected']for r in results)else'CONSTANT_PROOF_INCOMPLETE','image':'openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','cells':results,'constant_liberty_evidence':lib_evidence,'scope':'Actual final routed ODB output nets have one mapped driver with an actual standard-cell Liberty constant0 function. No data timing arc is fabricated. Only these exact ports/ODB identities are discharged.'};(W/'constant_proof.json').write_text(json.dumps(report,indent=1)+'\n');print(report['status']);print([(r['cell'],r['proved'],r['expected'])for r in results])
