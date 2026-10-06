from pathlib import Path
import os,time,json,subprocess,hashlib,sys,traceback
root=Path('/srv/opentallas-scratch2/jobs/mencius-window-writer-fullshape-r10');src=root/'source_roomy';control=root/'control'
def fresh():
 a=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]];time.sleep(1);b=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]];d=[y-x for x,y in zip(a,b)]
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 def free(p):v=os.statvfs(p);return v.f_bavail*v.f_frsize
 return dict(time=time.time(),load=os.getloadavg(),idle_cores=os.cpu_count()*sum(d[3:5])/sum(d[:8]),mem_available_bytes=mem,NVMe_free_bytes=free(root),root_free_bytes=free('/'),NUM_CORES=16,admission_GiB=40,required_NVMe_bytes=2*17321690829,capacity_basis='twice measured original fullshape physical run footprint17.322GB; original floorplan peak19.771GiB ->40GiB honest memory estimate')
def verify():
 rec=json.loads((control/'source_roomy_verified.json').read_text())
 for name,digest in rec['files'].items():assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True)
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==rec['prepared_snapshot_pin']
def guard(record):
 assert record['load'][0]<128 and record['idle_cores']>=16
 assert record['NVMe_free_bytes']>=record['required_NVMe_bytes'] and record['root_free_bytes']>0
try:
 verify();phase='postguard' if '--admitted' in sys.argv else 'preexec';r=fresh();(control/(phase+'_roomy.json')).write_text(json.dumps(r,indent=2)+'\n');guard(r)
 if phase=='preexec':
  (control/'started_roomy.json').write_text(json.dumps(dict(supervisor=os.getpid(),source='a70dde1e58236a11f761ec6fbeeccfd3ca0b2c77',time=time.time(),phase='waiting unchangedadmit40'))+'\n')
  code=subprocess.call(['/srv/opentallas-scratch/admit.sh','40','--',sys.executable,str(Path(__file__)), '--admitted'])
  (control/'terminal_roomy.exit').write_text(str(code)+'\n');sys.exit(code)
 env=dict(os.environ,OPENTALLAS_ORFS_IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29',TMPDIR=str(root/'tmp'),NUM_CORES='16',OT_ORFS_NUM_CORES='16')
 (root/'tmp').mkdir(exist_ok=True)
 cmd=[sys.executable,'tools/dsrom_window_pipeline_physical.py','--out',str(root/'run_roomy'),'--pnr-stop-after','floorplan','--execute']
 with (root/'physical_roomy.log').open('w') as f:
  proc=subprocess.Popen(cmd,cwd=src,env=env,stdout=f,stderr=subprocess.STDOUT)
  (control/'driver_started_roomy.json').write_text(json.dumps(dict(admitted_wrapper=os.getpid(),driver=proc.pid,command=cmd,source='a70dde1e58236a11f761ec6fbeeccfd3ca0b2c77',time=time.time(),full_route=False,parent_proof=False))+'\n'); code=proc.wait()
 sys.exit(code)
except BaseException as e:
 if isinstance(e,SystemExit):raise
 traceback.print_exc();(control/'terminal_roomy.exit').write_text('1\n');raise
