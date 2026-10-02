import hashlib,json,struct,subprocess,time,sys
from pathlib import Path
out=Path('/home/ubuntu/w17-D1-disjoint-20261002-r1')
src=out/'source';obj=out/'obj'
capture=Path('/home/ubuntu/w17-D1-terminal-review-20261002-r1')
sys.path.insert(0,str(src/'tools'))
import w17_D1_compile_ownership_handoff as owner
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
r=json.loads((out/'verdict.json').read_text())
assert r['verdict']=='PASS_OBJECT_SHARD_ONLY' and r['exit_code']==0 and r['missing_targets']==[]
assert r['node']=='VM' and r['source_head']=='a93ac5a8c2312266213cc4f119aa2bd99175f52a'
assert r['input_hashes_verified']==4353 and r['argv'][-1]=='D1_VM_SHARD'
unit=subprocess.check_output(['systemctl','--user','show','w17-D1-disjoint-VM-20261002-r1.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','ControlGroup'],text=True)
u=dict(x.split('=',1) for x in unit.splitlines())
assert u['MainPID']=='0' and u['ActiveState']=='inactive' and u['ExecMainStatus']=='0' and u['ControlGroup']==''
containers=subprocess.check_output(['docker','ps','-a','--filter','name=w17-D1-disjoint-VM-20261002-r1','--format','{{.ID}} {{.Status}}'],text=True)
assert not containers.strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==r['source_head']
assert sha(out/'compile.log')==r['log_SHA256']
base=json.loads((capture/'quiescent_input_inventory.json').read_text())
a,b=owner.assignments(owner.targets((obj/'Vtb_D1_scope_core_classes.mk').read_text()))
assert len(a)==1286 and len(b)==2543 and not set(a)&set(b)
rows=[]
for name in b:
 p=obj/name
 with p.open('rb') as f:header=f.read(64)
 assert len(header)==64 and header[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',header,16)==(1,62),name
 offset=struct.unpack_from('<Q',header,40)[0];width,count=struct.unpack_from('<HH',header,58)
 stat=p.stat();assert offset>=64 and width==64 and count>0 and stat.st_size>=offset+width*count,name
 digest=sha(p);assert (stat.st_size,stat.st_mtime_ns)==(p.stat().st_size,p.stat().st_mtime_ns),name
 rows.append({'target':name,'bytes':stat.st_size,'SHA256':digest,'owner':'VM','dependency_SHA256':sha(p.with_suffix('.d'))})
unchanged=[];retained=[]
for name,v in base.items():
 if name.endswith('.d'):continue
 assert sha(obj/name)==v['SHA256'],name
 (retained if name.endswith('.o') else unchanged).append(name)
assert len(retained)==252
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  if b'cc1plus' in (p/'cmdline').read_bytes() and str((p/'cwd').resolve()) in (str(obj),'/work/obj'):active.append(p.name)
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
assert not active
record={'verdict':'PASS_VM_TERMINAL_OBJECT_IDENTITY','epoch':time.time(),'owned_targets':len(rows),'source_head':r['source_head'],'generated_classes_SHA256':sha(obj/'Vtb_D1_scope_core_classes.mk'),'retained_local_objects_byteidentical':len(retained),'immutable_input_files_byteidentical':len(unchanged),'retained_PCH_byteidentical':sum(x.endswith('.gch') for x in unchanged),'unit':u,'container_absent':True,'active_compilers':active,'objects':rows,'runtime_started':False}
(capture/'object_identity.json').write_text(json.dumps(record,indent=2)+'\n')
(capture/'unit_terminal.txt').write_text(unit)
files=['verdict.json','compile.log','start.json','progress.json','obj/Vtb_D1_scope_core_classes.mk']+['obj/'+name for x in b for name in (x,Path(x).with_suffix('.d').name)]
(capture/'transfer_files.txt').write_text('\n'.join(files)+'\n')
(capture/'transfer_SHA256.json').write_text(json.dumps({name:sha(out/name) for name in files},indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='objects'}));print('receipt_SHA256',sha(capture/'object_identity.json'))
