import concurrent.futures,subprocess,json,pathlib
A=pathlib.Path(__file__).resolve().parent
code="""import json,subprocess
rows=[]
for cid in subprocess.check_output(['docker','ps','-q'],text=True).split():
 d=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
 mounts=[m for m in d.get('Mounts',[]) if '/hd4g/gen2e2' in m.get('Source','')]
 if mounts: rows.append({'id':cid,'name':d['Name'],'pid':d['State']['Pid'],'started':d['State']['StartedAt'],'mounts':mounts,'path':d['Path'],'args':d['Args']})
print(json.dumps(rows))"""
def one(host):
 try:
  p=subprocess.run(['ssh','-o','ConnectTimeout=8',host,'python3 -'],input=code,text=True,capture_output=True,timeout=100)
  return host,{'rc':p.returncode,'rows':json.loads(p.stdout) if p.returncode==0 else p.stderr}
 except Exception as e:return host,{'error':str(e)}
r=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(one,['ot-epyc4','ot-epyc5','ot-epyc6','ot-epyc8','ot-pve1','ot-pve2','ot-pve3']))
(A/'original_live_inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print({h:len(x.get('rows',[])) if x.get('rc')==0 else x for h,x in r.items()})
