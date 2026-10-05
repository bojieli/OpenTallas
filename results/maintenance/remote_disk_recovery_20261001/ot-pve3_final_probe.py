import os,json,pathlib as P,subprocess as S,time,shutil
checks=[{'path': '/tmp/claude-1000/pxw2', 'ref': 'refs/maintenance/remote-recovery-20261001/retired-e5bc5283785c21c2', 'head': 'fd852d7a0cac9ee2d56219b9a2bae892691e6509'}, {'path': '/tmp/claude-1000/pxw3', 'ref': 'refs/maintenance/remote-recovery-20261001/retired-2fa1266ece02d60d', 'head': 'fd852d7a0cac9ee2d56219b9a2bae892691e6509'}]

v=os.statvfs('/home/ubuntu');mem={k:int(x.strip().split()[0])*1024 for k,x in (l.split(':',1) for l in P.Path('/proc/meminfo').read_text().splitlines())};r={'timestamp':time.time(),'disk_free_bytes':v.f_bavail*v.f_frsize,'mem_available_bytes':mem['MemAvailable'],'mem_total_bytes':mem['MemTotal'],'cpu_count':os.cpu_count(),'loadavg':os.getloadavg(),'preserved_head_checks':[]}
for c in checks:
 got=S.check_output(['git','--git-dir','/home/ubuntu/repo.git','rev-parse',c['ref']],text=True).strip();ok=got==c['head'] and not P.Path(c['path']).exists();assert ok,c;r['preserved_head_checks'].append({**c,'verified':ok})
p=S.run(['docker','ps','--format','{{.ID}} {{.Names}}'],capture_output=True,text=True);r['docker_ps_returncode']=p.returncode;r['running_containers']=p.stdout.splitlines();r['docker_error']=p.stderr
print(json.dumps(r))
