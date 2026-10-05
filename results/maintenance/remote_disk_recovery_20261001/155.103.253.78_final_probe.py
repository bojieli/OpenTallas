import os,json,pathlib as P,subprocess as S,time,shutil
checks=[{'path': '/home/ubuntu/v41bt/wtG', 'ref': 'refs/maintenance/remote-recovery-20261001/retired-f8f3fea1e79e4d50', 'head': '95b9b7825f8f7f8324fb17220f6dab04c945223d'}, {'path': '/home/ubuntu/v41bt/wtH', 'ref': 'refs/maintenance/remote-recovery-20261001/retired-73a467a572d26e9e', 'head': '95b9b7825f8f7f8324fb17220f6dab04c945223d'}, {'path': '/home/ubuntu/w15bwt3', 'ref': 'refs/maintenance/remote-recovery-20261001/retired-b6f06b5a1863edc9', 'head': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1'}]

v=os.statvfs('/home/ubuntu');mem={k:int(x.strip().split()[0])*1024 for k,x in (l.split(':',1) for l in P.Path('/proc/meminfo').read_text().splitlines())};r={'timestamp':time.time(),'disk_free_bytes':v.f_bavail*v.f_frsize,'mem_available_bytes':mem['MemAvailable'],'mem_total_bytes':mem['MemTotal'],'cpu_count':os.cpu_count(),'loadavg':os.getloadavg(),'preserved_head_checks':[]}
for c in checks:
 got=S.check_output(['git','--git-dir','/home/ubuntu/repo.git','rev-parse',c['ref']],text=True).strip();ok=got==c['head'] and not P.Path(c['path']).exists();assert ok,c;r['preserved_head_checks'].append({**c,'verified':ok})
p=S.run(['docker','ps','--format','{{.ID}} {{.Names}}'],capture_output=True,text=True);r['docker_ps_returncode']=p.returncode;r['running_containers']=p.stdout.splitlines();r['docker_error']=p.stderr
print(json.dumps(r))
