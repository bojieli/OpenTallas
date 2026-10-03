import os,json,pathlib,hashlib,time
root=pathlib.Path('/home/ubuntu/w6');files=[];refs=[];records=[];errors=[]
for p in root.rglob('*'):
 try:
  if not p.is_file():continue
  s=p.stat();files.append(dict(path=str(p),bytes=s.st_size,device=s.st_dev,inode=s.st_ino,mtime_ns=s.st_mtime_ns,allocated_bytes=s.st_blocks*512))
  scan=p.suffix in ['.json','.log','.py','.sh','.sv','.v','.tcl','.mk','.txt','.f','.dat'] and s.st_size<=2000000
  if scan:
   raw=p.read_bytes()
   if b'\0' in raw[:4096]:continue
   text=raw.decode(errors='replace');matches=[]
   for lineno,line in enumerate(text.splitlines(),1):
    if any(t in line for t in ['/home/ubuntu/w6','/tmp/claude-1000/w6img','w6-exec','matrix_int8.hex','img2/']):matches.append(dict(line=lineno,text=line[:1200]))
   if matches:refs.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),matches=matches[:30],total_matches=len(matches)))
   if p.suffix in ['.json','.log','.dat'] or p.name=='emit.sh':records.append(dict(path=str(p),bytes=s.st_size,sha256=hashlib.sha256(raw).hexdigest()))
 except OSError as e:errors.append(dict(path=str(p),error=str(e)))
print(json.dumps(dict(time_ns=time.time_ns(),root=str(root),files=files,historical_text_consumers=refs,small_evidence_records=records,errors=errors,scan_scope='textsource/manifest/log <=2MB only; no candidate weight content or compiled binary content read',no_deletion=True),indent=2))
