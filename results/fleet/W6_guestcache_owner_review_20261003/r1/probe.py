import os,json,time,pathlib,subprocess,hashlib,platform
rows=json.load(open('/tmp/Goodall-W6-cache-owner-review-20261003/candidates.json'))
keys={(r['device'],r['inode']):r['path'] for r in rows}
out={'time_ns':time.time_ns(),'hostname':platform.node(),'kernel':platform.release(),'candidate_count':len(rows),'metadata':[],'references':[],'proc_errors':[],'no_content_reads_of_candidate_files':True,'dirty_writeback_file_specific':'UNKNOWN: kernel 5.15 predates cachestat; no candidate mapping or content fault performed','deletion':False,'cache_advice':False}
for r in rows:
 try:
  s=os.stat(r['path']); q={k:getattr(s,'st_'+k) for k in ['dev','ino','size','mtime_ns','nlink']};q['path']=r['path']; q['historical_identity_match']=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(r['device'],r['inode'],r['bytes'],r['mtime_ns']);out['metadata'].append(q)
 except OSError as e:out['metadata'].append({'path':r['path'],'error':str(e)})
for pd in pathlib.Path('/proc').iterdir():
 if not pd.name.isdecimal() or int(pd.name)==os.getpid():continue
 try:
  cmd=(pd/'cmdline').read_bytes().replace(b'\0',b' ')
  if b'/home/ubuntu/w6' in cmd:out['references'].append({'pid':int(pd.name),'kind':'argv_root','cmd_sha256':hashlib.sha256(cmd).hexdigest()})
  for name in ['cwd','exe','root']:
   try:
    value=os.readlink(pd/name)
    if value=='/home/ubuntu/w6' or value.startswith('/home/ubuntu/w6/'):out['references'].append({'pid':int(pd.name),'kind':name,'path':value})
   except FileNotFoundError:pass
  for fd in (pd/'fd').iterdir():
   try:
    s=fd.stat(); key=(s.st_dev,s.st_ino)
    target=os.readlink(fd)
    if key in keys or target=='/home/ubuntu/w6' or target.startswith('/home/ubuntu/w6/'):
     out['references'].append({'pid':int(pd.name),'kind':'fd','fd':fd.name,'path':target,'candidate':keys.get(key)})
   except FileNotFoundError:pass
  for line in (pd/'maps').read_text().splitlines():
   fs=line.split(None,5)
   if len(fs)<5:continue
   major,minor=(int(x,16) for x in fs[3].split(':'));key=(os.makedev(major,minor),int(fs[4]))
   if key in keys or (len(fs)>5 and fs[5].startswith('/home/ubuntu/w6/')):out['references'].append({'pid':int(pd.name),'kind':'mmap','path':fs[5] if len(fs)>5 else None,'candidate':keys.get(key)})
 except FileNotFoundError:pass
 except (PermissionError,OSError) as e:out['proc_errors'].append({'pid':int(pd.name),'error':str(e)})
out['completed_ns']=time.time_ns();out['identity_all_match']=all(r.get('historical_identity_match') for r in out['metadata']);print(json.dumps(out,indent=2))
