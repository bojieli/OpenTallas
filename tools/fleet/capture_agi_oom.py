import json,subprocess,datetime, pathlib
ids=subprocess.check_output(['sudo','docker','ps','-q'],text=True).split()
containers=json.loads(subprocess.check_output(['sudo','docker','inspect',*ids],text=True)) if ids else []
r={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'meminfo':pathlib.Path('/proc/meminfo').read_text(),'loadavg':pathlib.Path('/proc/loadavg').read_text(),'containers':[],'large_processes':[]}
for c in containers:
 pid=c['State']['Pid']; d={'id':c['Id'],'name':c['Name'],'pid':pid,'started':c['State']['StartedAt'],'memory_limit_bytes':c['HostConfig']['Memory'],'mounts':[x['Source'] for x in c['Mounts']]}
 try:
  cg=pathlib.Path('/proc/'+str(pid)+'/cgroup').read_text().split('::')[1].strip(); base=pathlib.Path('/sys/fs/cgroup'+cg)
  d['cgroup']={k:(base/k).read_text().strip() for k in ['memory.current','memory.peak','memory.events'] if (base/k).exists()}
 except Exception as e:d['cgroup_error']=str(e)
 r['containers'].append(d)
for pp in pathlib.Path('/proc').iterdir():
 if not pp.name.isdigit():continue
 try:
  status=pp.joinpath('status').read_text(); vals=dict(x.split(':',1) for x in status.splitlines() if ':' in x)
  rss=int(vals.get('VmRSS','0 kB').split()[0])
  if rss>512*1024:r['large_processes'].append({'pid':int(pp.name),'name':vals['Name'].strip(),'rss_kib':rss,'hwm':vals.get('VmHWM','').strip(),'ppid':vals['PPid'].strip(),'cwd':str(pp.joinpath('cwd').resolve())})
 except:pass
r['kernel_oom']=subprocess.check_output(['sudo','journalctl','-k','--since','2026-10-10 05:15:00','--until','2026-10-10 05:25:00','--no-pager'],text=True)
print(json.dumps(r,indent=2))
