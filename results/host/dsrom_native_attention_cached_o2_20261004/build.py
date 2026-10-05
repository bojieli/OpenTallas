from pathlib import Path
import hashlib,json,subprocess,time,shutil,os,sys,re
root=Path('/srv/opentallas-scratch/builds/goodall-s81-native-attention-cached-o2-20261004-r1')
out=root/'out'
identity=json.loads((out/'input-identity.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(name,data):
 with (root/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
for name,pin in identity['files'].items():
 p=out/name
 assert p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],name
assert not list(out.rglob('*.o')) and not list(out.rglob('*.a')) and not list(out.rglob('*.gch'))
mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if len(l.split())>=2 and l.split()[1].isdigit()}
assert mem['MemAvailable']>=132*1024**3,'fresh measured memory admission lost: 32GiB estimate + host100GiB reserve'
assert shutil.disk_usage(root).free>=32*1024**3,'output headroom lost'
# ONLY copied makefiles change: preserve fPIC/defines/ABI, replace -O0.
changed={}
for name in identity['files']:
 p=out/name
 if p.suffix=='.mk':
  text=p.read_text();new=text.replace('-O0','-O2 -ffp-contract=off')
  if new!=text:p.write_text(new);changed[name]=sha(p)
write('compile-flag-delta.json',changed)
start=time.time();commands=[];stages=[]
write('build-start.json',dict(start_unix=start,memory_available=mem['MemAvailable'],disk_available=shutil.disk_usage(root).free,workers=16,memory_scheduling_estimate_bytes=32*1024**3,runtime_cap=None,memory_cap=None,scope='unchanged cached ATT generated CXX only; no HDL generation or runtime'))
def build(directory,prefix,target):
 # Disable ONLY the generated HDL-relaunch make include. Cached CXX remains
 # unchanged; children are built explicitly, then the required closure joined.
 command=['make','-C',str(directory),'-f',prefix+'.mk','-j16','OPT_FAST=-O2','OPT_SLOW=-O2','OPT_GLOBAL=-O2','CXX=g++-15','LINK=g++-15','VM_HIER_VERILATION_INCLUDED=1','VM_HIER_LIBS=',target]
 commands.append(command);(root/'build.argv.json').write_text(json.dumps(commands,indent=2)+'\n')
 log=root/(prefix+'.log');stamp=time.time()
 with log.open('x') as f:
  rc=subprocess.call(['/usr/bin/time','-v','-o',str(root/(prefix+'.time')),*command],stdout=f,stderr=subprocess.STDOUT)
 stages.append(dict(prefix=prefix,exit=rc,wall_seconds=time.time()-stamp))
 write(prefix+'-end.json',stages[-1])
 if rc:raise RuntimeError('CXX failed '+prefix+' exit '+str(rc))
 assert ' -O0' not in log.read_text() and '-ffast-math' not in log.read_text() and '-Ofast' not in log.read_text()
engine=out/'engine'
children=[('Vot_hdc_qadd','libot_hdc_qadd.a'),('Vot_hdc_v41x_attn_staging_3','libot_hdc_v41x_attn_staging_3.a'),('Vot_hdc_v41x_attn_tile_e','libot_hdc_v41x_attn_tile_e.a'),('Vot_hdc_v41x_attn_merge_6','libot_hdc_v41x_attn_merge_6.a')]
try:
 for prefix,target in children:build(engine/prefix,prefix,target)
 build(engine,'VDsromAttEngine','VDsromAttEngine__ALL.a')
 build(out/'adapter','VDsromAttention','VDsromAttention__ALL.a')
 # Fresh archive from a unique object closure. Never append into populated
 # archives, run make -n, or mutate the old delivered archive set.
 model=engine/'VDsromAttEngine__MODEL.a';(engine/'VDsromAttEngine__ALL.a').rename(model)
 parts=[model]+[engine/prefix/target for prefix,target in children]
 unique={};merge=root/'merge';merge.mkdir()
 for index,part in enumerate(parts):
  names=subprocess.check_output(['ar','t',str(part)],text=True).splitlines()
  assert len(names)==len(set(names)),('duplicate fresh member',part)
  extract=merge/str(index);extract.mkdir()
  subprocess.run(['ar','x',str(part)],cwd=extract,check=True)
  for name in names:
   assert name==Path(name).name and name not in ('.','..'),name
   obj=extract/name;pin=sha(obj)
   if name in unique:assert unique[name][1]==pin,('different objects share name',name)
   else:unique[name]=(obj,pin)
 response=root/'unique-objects.rsp'
 response.write_text('\n'.join(str(p) for p,_ in unique.values())+'\n')
 combined=engine/'VDsromAttEngine__ALL.a';assert not combined.exists()
 subprocess.run(['ar','rcs',str(combined),'@'+str(response)],check=True)
 assert len(subprocess.check_output(['ar','t',str(combined)],text=True).splitlines())==len(unique)
 for name,pin in identity['files'].items():
  assert sha(out/name)==changed.get(name,pin['sha256']),('cached input changed',name)
 archives=[combined,out/'adapter/VDsromAttention__ALL.a']+[engine/prefix/target for prefix,target in children]
 terminal=dict(verdict='PASS_STRICT_O2_CACHED_ATT_ARCHIVES_ONLY',exit=0,wall_seconds=time.time()-start,stages=stages,generated_cpp_headers_unchanged=True,unique_engine_members=len(unique),archives={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in archives},scope='host compile optimization only; no runtime/numerical/clock/physical/rate credit')
except Exception as exc:
 terminal=dict(verdict='FAIL_CXX_OR_ARCHIVE',exit=1,wall_seconds=time.time()-start,stages=stages,failure=str(exc))
write('terminal.json',terminal);print(json.dumps(terminal),flush=True);sys.exit(terminal['exit'])
