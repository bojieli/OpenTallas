import json,os,pathlib,shutil,subprocess,time,hashlib
root=pathlib.Path(__file__).resolve().parent;src=root.parent/'src';work=root/'work/orfs'
assert not (root/'native.started').exists()
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain'],text=True)
commit=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip();assert commit=='d42ab03089f6da7a0f747f5bb4bbbc2a2debbb38'
m=json.loads((src/'results/uarch/hbm_attn_h16_context_20261005/model.json').read_text())
for n,h in m['source_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
def cpu():return list(map(int,pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
a=cpu();time.sleep(2);b=cpu();idle=os.cpu_count()*(b[3]-a[3])/sum(y-x for x,y in zip(a,b));available=int(next(l.split()[1] for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;free=shutil.disk_usage(root).free
r=dict(utc=time.strftime('%FT%TZ',time.gmtime()),idle_cores=idle,workers=16,load=os.getloadavg(),MemAvailable_GiB=available/2**30,disk_free_GiB=free/2**30,expected_peak_GiB=32,memory_reserve_GiB=100,disk_inventory_reserve_GiB=16,source_commit=commit)
(root/'fresh_capacity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if r['load'][0]>=128 or idle<16 or available<132*2**30 or free<16*2**30:raise SystemExit('CAPACITY_REFUSAL: resume unstarted')
oldfiles=[p for p in (work/'results').rglob('*') if p.is_file()]
oldopts=['--old-file=/work/'+str(p.relative_to(work)) for p in oldfiles]
# Freeze only actual completed synthesis/floorplan targets. Failed macro placement has no ODB target.
assert any(p.name=='2_1_floorplan.odb' for p in oldfiles)
make='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 '+' '.join(oldopts)+' finish metadata-generate'
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd=['docker','run','--rm','--name','codex_lagrange_h16_pdn_resume_20261005','-v',str(src)+':/src:ro','-v',str(work)+':/work','-w','/OpenROAD-flow-scripts/flow',image,'bash','-lc',"trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && "+make]
(root/'argv.json').write_text(json.dumps(cmd,indent=2)+'\n');(root/'native.started').write_text(r['utc']+'\n')
with (root/'run.log').open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(root/'exit').write_text('native_rc='+str(p.returncode)+'\n')
# A completed native flow is evaluated using the retained independent SS/FF helper, image pinned to the same digest.
if list((work/'results').rglob('6_final.spef')):
 import importlib.util
 spec=importlib.util.spec_from_file_location('corner_sta',src/'tools/w18/corner_sta.py');cs=importlib.util.module_from_spec(spec);spec.loader.exec_module(cs)
 real_run=cs.subprocess.run
 def pinned_run(cmd,*args,**kwargs):
  if isinstance(cmd,list):cmd=[image if v=='openroad/orfs:latest' else v for v in cmd]
  return real_run(cmd,*args,**kwargs)
 cs.subprocess.run=pinned_run
 with (root/'corner.log').open('w') as f:
  import contextlib
  with contextlib.redirect_stdout(f):cs.main(['--orfs-dir',str(work),'--macro','physical/hbm_fmax_attn_context/ot_attn_hgrp_m6h1','--output',str(root/'corner_sta.json')])
(root/'end').write_text(time.strftime('%FT%TZ',time.gmtime())+'\n');print('native terminal rc',p.returncode,flush=True)
