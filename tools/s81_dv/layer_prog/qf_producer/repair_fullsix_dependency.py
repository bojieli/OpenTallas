#!/usr/bin/env python3
"""Freeze one omitted real CEA dependency in a fresh stage; never execute it."""
import json,hashlib,subprocess,shutil,re
from pathlib import Path
from head_local_contract import ROOT
b=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle'
out=b/'fullsix_frontend02_packet';out.mkdir(exist_ok=False)
path='rtl/hdc/ot_hdc_delay_rf.sv'
data=subprocess.check_output(['git','show','ceaed19c4:'+path])
sha=hashlib.sha256(data).hexdigest()
dst=out/'source_addition'/path;dst.parent.mkdir(parents=True);dst.write_bytes(data)
s=data.decode();assert '`include' not in s
assert len(re.findall(r'^module\s+',s,re.M))==1
assert not re.findall(r'^\s*[A-Za-z_]\w*\s+#\(',s,re.M)
src=subprocess.check_output(['git','show','ceaed19c4:rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv']).decode()
calls=[dict(line=i+1,text=l.strip()) for i,l in enumerate(src.splitlines()) if 'ot_hdc_delay_rf #' in l]
assert len(calls)==2
dependency=dict(path=path,ref='ceaed19c4',sha256=sha,bytes=len(data),modules=['ot_hdc_delay_rf'],actual_parent_path='rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv',actual_parent_sha256=hashlib.sha256(src.encode()).hexdigest(),calls=calls,recursive_closure='Self-contained module, no include/import/submodule instantiations: only din/dout/mem/wptr sequential state and combinational assigns. Existing return-tree register-file delay implementation, not new datapath hardware.')
base=b/'fullsix_launch_packet'
for n in ['frontend.sh','source_files.f','tb_fullsix_trace.sv','selected_fullsix_cone.sv','cells_used.v','trace_points.json']:
 shutil.copyfile(base/n,out/n)
with (out/'source_files.f').open('a') as f:f.write('src/'+path+'\n')
m=json.loads((b/'selected_vehicle_build_manifest.json').read_text());m['files'].append({k:dependency[k] for k in ['path','ref','sha256','bytes','modules']});m['source_bytes']+=len(data);m['source_module_definitions']+=1
m['scope']='Corrected126-source private frontend input manifest; missing real return-tree RF dependency added; no build receipt'
(out/'selected_vehicle_build_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
(out/'dependency_repair.json').write_text(json.dumps(dict(scope='Actual dependency omission repair only; frontend01 frozen failure retained',dependency=dependency,source_count_before=125,source_count_after=126,unchanged=['All125 original source bytes','Fullsix TB, clocks/reset,72 tracepoint bindings, actual43 selected statements','Weights/all1012frameROM+7XSROMs/CTL/gold/15epochs','Verilator settings, capacityreservation256GB/1thread/disk80GB, no process/wall limit','CAP reset CFG with faults retained; no numericPASS, nativeNULL, original deadlines'],changed=['One existing CEA source file added','source_files.f appends that existing module','Fresh fullsix_frontend_02 directory and source hash manifest']),indent=2)+'\n')
subprocess.run(['ssh','ot-epyc4','mkdir -p /srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_repair_inputs'],check=True)
subprocess.run(['scp',str(dst),str(out/'source_files.f'),str(out/'selected_vehicle_build_manifest.json'),'ot-epyc4:/srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_repair_inputs/'],check=True)
script=r'''
from pathlib import Path
import json,hashlib,shutil
lane=Path('/srv/opentallas-scratch/claude/s81-qf-producer-source-1019');old=lane/'fullsix_frontend_01';out=lane/'fullsix_frontend_02';repair=lane/'fullsix_repair_inputs'
if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
out.mkdir()
orig=json.load(open(old/'frozen_inputs.json'))
for r in orig['files']:
 p=old/r['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 q=out/r['path'];q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
path='rtl/hdc/ot_hdc_delay_rf.sv';q=out/'src'/path;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repair/'ot_hdc_delay_rf.sv',q)
for n in ['source_files.f','selected_vehicle_build_manifest.json']:shutil.copyfile(repair/n,out/n)
files=[]
for p in sorted(out.rglob('*')):
 if p.is_file():files.append(dict(path=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
now={r['path']:r for r in files};before={r['path']:r for r in orig['files']}
changed=[p for p in now.keys()&before.keys() if now[p]['sha256']!=before[p]['sha256']]
assert sorted(changed)==['selected_vehicle_build_manifest.json','source_files.f']
assert set(now)-set(before)=={'src/'+path}
for r in json.load(open(out/'selected_vehicle_build_manifest.json'))['files']:assert hashlib.sha256((out/'src'/r['path']).read_bytes()).hexdigest()==r['sha256']
(out/'frozen_inputs.json').write_text(json.dumps(dict(scope='Corrected actual126-source immutable stage only; no frontend/build',files=files,files_count=len(files),bytes=sum(r['bytes'] for r in files),diff_from_frontend01=dict(added=['src/'+path],changed=changed),nativephase=None,numeric_PASS=None),indent=2)+'\n')
print('STAGED_NO_BUILD',len(files),sum(r['bytes'] for r in files),changed)
'''
subprocess.run(['ssh','ot-epyc4','python3 -'],input=script.encode(),check=True)
subprocess.run(['scp','ot-epyc4:/srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_frontend_02/frozen_inputs.json',str(out/'frozen_inputs.json')],check=True)
print('Corrected source126 stage only',sha)
