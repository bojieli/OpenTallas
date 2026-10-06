import json,os,pathlib,shutil,subprocess,time
root=pathlib.Path(__file__).resolve().parent
assert not (root/'native.started').exists()
def sample():
 a=list(map(int,pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));time.sleep(2);b=list(map(int,pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));idle=os.cpu_count()*(b[3]-a[3])/sum(y-x for x,y in zip(a,b));available=int(next(l.split()[1] for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;free=shutil.disk_usage(root).free
 return dict(utc=time.strftime('%FT%TZ',time.gmtime()),idle_cores=idle,workers=1,MemAvailable_GiB=available/2**30,disk_free_GiB=free/2**30,load=os.getloadavg(),expected_peak_GiB=8,memory_reserve_GiB=100,disk_inventory_reserve_GiB=8)
r=sample();(root/'fresh_capacity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if r['load'][0]>=128 or r['idle_cores']<1 or r['MemAvailable_GiB']<108 or r['disk_free_GiB']<8:raise SystemExit('CAPACITY_REFUSAL: diagnostic unstarted')
original=root/'original_physical.json';d=json.loads(original.read_text());src=root/'source'
import hashlib
for a in d['design']['sources']:assert hashlib.sha256((src/a['path']).read_bytes()).hexdigest()==a['sha256'],a['path']
cmd=['docker','run','--rm','--name','codex_lagrange_ctl64_d760_diag_20261005','-v',str(src)+':/src:ro','-v',str(root/'work')+':/work','-v',str(root)+':/diag','-w','/OpenROAD-flow-scripts/flow','openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc',"trap 'chmod -R a+rwX /work /diag >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /diag/patch_new_container.py && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=1 do-4_1_cts"]
(root/'argv.json').write_text(json.dumps(cmd,indent=2)+'\n');(root/'native.started').write_text(r['utc']+'\n')
with (root/'run.log').open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(root/'exit').write_text('rc='+str(p.returncode)+'\n');print('diagnostic terminal rc',p.returncode,flush=True)
