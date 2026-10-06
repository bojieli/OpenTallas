import hashlib,json,os,pathlib,shutil,subprocess,time
root=pathlib.Path(__file__).resolve().parent
src=root/'src'
def capacity():
 a=list(map(int,pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));time.sleep(2);b=list(map(int,pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return dict(utc=time.strftime('%FT%TZ',time.gmtime()),load=os.getloadavg(),idle_cores=os.cpu_count()*(b[3]-a[3])/sum(y-x for x,y in zip(a,b)),MemAvailable_GiB=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))/2**20,disk_free_GiB=shutil.disk_usage(root).free/2**30,workers=8,expected_memory_GiB=16,required_host_memory_reserve_GiB=100,disk_inventory_GiB=8)
def check(tag):
 c=capacity();(root/(tag+'.json')).write_text(json.dumps(c,indent=2)+'\n');print(tag,json.dumps(c),flush=True)
 assert c['load'][0]<128 and c['idle_cores']>=8 and c['MemAvailable_GiB']>=116 and c['disk_free_GiB']>=8,'CAPACITY_REFUSAL unstarted'
if '--guarded' not in __import__('sys').argv:
 assert not(root/'native.started').exists()
 check('before_guard_capacity')
 raise SystemExit(subprocess.call(['/srv/opentallas-scratch/admit.sh','16','--','python3',str(root/'run_exact.py'),'--guarded']))
check('fresh_capacity')
assert subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True)==''
rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip();assert rev.startswith('1659b138d')
m=json.loads((src/'results/uarch/hbm_su_ctl_registered_closure_20261005/model.json').read_text())
for path,digest in m['source_sha256'].items():assert hashlib.sha256((src/path).read_bytes()).hexdigest()==digest,path
cmd=['python3','tools/hbm_su_ctl_c13.py','su-run','--out',str(root/'out'),'--work',str(root/'work'),'--n','64','--m','16','--bcast','7','--ret','8','--fp','dpi_beh','--cases','su_cases_v2_ildr.pkl']
(root/'argv.json').write_text(json.dumps(cmd,indent=2)+'\n');(root/'native.started').write_text(time.strftime('%FT%TZ',time.gmtime())+'\n');(root/'pid').write_text(str(os.getpid())+'\n')
with(root/'run.log').open('w') as f:r=subprocess.run(cmd,cwd=src,stdout=f,stderr=subprocess.STDOUT)
(root/'exit').write_text('rc='+str(r.returncode)+'\n');print('TERMINAL',r.returncode,flush=True)
