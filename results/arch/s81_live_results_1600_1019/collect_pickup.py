import concurrent.futures, datetime, hashlib, json, pathlib, re, subprocess
WT=pathlib.Path(__file__).resolve().parents[3]
OUT=WT/'results/arch/s81_live_results_1600_1019'
OUT.mkdir(parents=True,exist_ok=True)
REMOTE='''import datetime,hashlib,json,pathlib,subprocess,sys
cfg=json.loads(sys.argv[1]); out={'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
out['ps']=subprocess.run(['ps','-p',','.join(map(str,cfg['pids'])),'-o','pid,ppid,etime,pcpu,rss,args'],capture_output=True,text=True).stdout
for name in cfg['paths']:
 p=pathlib.Path(name)
 try:
  b=p.read_bytes(); t=b.decode(errors='replace'); lines=t.splitlines()
  selected=[x for x in lines if x.startswith(('GATE_SOURCE_ARCHIVE_SHA256=','GATE_GRT_RC=','GATE_DONE','GATE_SCRIPT_RC=','GATE_PC ','GATE_CK ss','GATE_FLOW_RC='))]
  selected+=[x for x in lines if '[ERROR ' in x or 'GRT-0115' in x or 'read_liberty ' in x]
  selected+=lines[-18:]
  rec={'path':name,'size':len(b),'mtime_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(b).hexdigest(),'selected_lines':[x if len(x)<4000 else x[:180]+' [OMITTED LONG LINE '+str(len(x))+' characters]' for x in selected]}
  if name.endswith('.json'): rec['json']=json.loads(t)
  out['files'].append(rec)
 except Exception as e: out['files'].append({'path':name,'error':str(e)})
print(json.dumps(out,indent=2))
'''
pids={'ot-epyc4':[541823], 'ot-epyc6':[4183827,4069913], 'ot-epyc7':[120653,2329250,3654923,3743357,3743383,4043172,4089104], 'ot-epyc8':[724195,1174997]}
def one(host):
 paths=[]
 for suffix in ['', '-focused','-progress']:
  s=subprocess.run(['git','-C',str(WT),'show',f'38ac12f1f:results/arch/s81_live_results_1507_1019/{host}{suffix}.txt'],capture_output=True,text=True).stdout
  for name in re.findall(r'^FILE (\S+)',s,re.M):
   if 's10b-' not in name and name not in paths: paths.append(name)
 # Inspect exact sibling finalized route/CTS outputs when the previous file was temporary.
 for name in list(paths):
  if name.endswith('.tmp.log'):
   for ext in ['.log','.json']:
    other=name[:-8]+ext
    if other not in paths: paths.append(other)
 cfg={'paths':paths,'pids':pids[host]}
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3','-c',__import__('shlex').quote(REMOTE),__import__('shlex').quote(json.dumps(cfg))],capture_output=True,text=True,timeout=115)
 (OUT/(host+'.json')).write_text(p.stdout)
 if p.stderr: (OUT/(host+'.stderr')).write_text(p.stderr)
 return host,p.returncode,len(p.stdout)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for x in pool.map(one,pids): print(x)
