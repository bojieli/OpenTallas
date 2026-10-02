#!/usr/bin/env python3
"""Read-only failed-build census; no compiler or build is invoked."""
import json,hashlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PRIOR=Path('/tmp/hbm-native-connected-reuse-parent-20261002-r1')
OUT=ROOT/'results/uarch/hbm_connected_cxx_calibration_r6_20261002'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def census():
 manifest=ROOT/'results/uarch/hbm_rf_connected_reuse_r5_20261002/DS_frontend_inventory.json'
 m=json.loads(manifest.read_text());obj=PRIOR/'DS/obj';groups={};group=None
 for line in (obj/'Vconnected_classes.mk').read_text().splitlines():
  s=line.strip()
  if s.startswith('VM_') and (' +=' in s or ' =' in s):group=s.split()[0];groups.setdefault(group,[])
  elif group and s.startswith(('Vconnected','verilated')):groups[group].extend(s.rstrip('\\').split())
  else:group=None
 inventory={x['path']:x for x in m['files']};units=[];start=(PRIOR/'DS-CXX-start.json').stat().st_mtime_ns
 for group,names in groups.items():
  for name in names:
   src=inventory.get(name+'.cpp')
   if src is None:
    runtime=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')/(name+'.cpp')
    src={'path':str(runtime),'bytes':runtime.stat().st_size,'sha256':sha(runtime)}
   p=obj/(name+'.o');record={'name':name,'group':group,'source':src,'object_present':p.exists(),'individual_wall_s':None,'individual_cpu_s':None}
   if p.exists():
    data=p.read_bytes();st=p.stat();record.update(object_bytes=len(data),object_sha256=hashlib.sha256(data).hexdigest(),completion_offset_from_start_receipt_s=(st.st_mtime_ns-start)/1e9,ELF_magic=data[:4]==b'\x7fELF')
    # Header/section table extent check only; neither linker nor semantic validation.
    record['ELF_section_table_in_bounds']=False
    if len(data)>=64 and data[:6]==b'\x7fELF\x02\x01':
     offset=struct.unpack_from('<Q',data,40)[0];size,count=struct.unpack_from('<HH',data,58)
     record['ELF_section_table_in_bounds']=offset>0 and count>0 and offset+size*count<=len(data)
   units.append(record)
 summary={g:{'translation_units':len(ns),'source_bytes':sum(u['source']['bytes']for u in units if u['group']==g and u['source']),'objects_present':sum(u['object_present']for u in units if u['group']==g),'object_bytes':sum(u.get('object_bytes',0)for u in units if u['group']==g),'ELF_section_table_in_bounds':sum(u.get('ELF_section_table_in_bounds',False)for u in units if u['group']==g)}for g,ns in groups.items() if ns}
 for g,values in summary.items():
  sizes=sorted(u['source']['bytes']for u in units if u['group']==g)
  values['source_size_min_median_max_bytes']=[sizes[0],sizes[len(sizes)//2],sizes[-1]]
 end=json.loads((PRIOR/'DS-CXX-end.json').read_text())
 return {'schema':'opentallas.H1.CXX-resource-calibration.v1','prior_failure_commit':'c51502d2e2019058fbb199adc4a4cfbf599b373a','prior_output':str(PRIOR),'prior_GO_commit':'6d0cff62972fe3b5ddeaf6e9a1bfd49080617966','failure_pins':{str(p.relative_to(PRIOR)):sha(p)for p in [PRIOR/'verdict.json',PRIOR/'DS-CXX-start.json',PRIOR/'DS-CXX-end.json',PRIOR/'DS/CXX.log']},'generated_inventory_sha256':sha(manifest),'dependency_files_sha256':{str(p):sha(p)for p in [obj/'Vconnected.mk',obj/'Vconnected_classes.mk',Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include/verilated.mk')]},'observed_CXX':end,'groups':summary,'units':units,'cost_observability':'Per-unit source/object sizes and object mtime offsets measured. Concurrent compiler launches lack start/CPU timestamps; individual duration and CPU cost are unidentifiable. Header extent checks do not certify completed objects. All failed objects excluded from reuse.','dependency_critical_path':{'graph':'PCH fast -> fast objects; PCH slow -> slow/support objects; generated makefile -> runtime objects; all generated objects -> archive -> link with runtime objects -> simulation -> trace. VM_PARALLEL_BUILDS=1.','quantified_wall_s':None,'PCH_bytes':{p.name:p.stat().st_size for p in obj.glob('*.gch')},'unknown':'Remaining slow/support compiler costs, maximum TU critical path, archive/link cost, cache contention and Qwen frontend remain unmeasured.'},'resource_model':{'candidate_affinity':list(range(8,24)),'make_jobs':16,'CXX_budget_s_each':1800,'whole_wall_s':4620,'memory_bytes':32*1024**3,'swap_bytes':0,'observed_parent_memory_approx_bytes':3*1024**3,'memory_projection':'A proportional 4-to-16 slot extrapolation of the approximately3GiB observed envelope is approximately12GiB, below32GiB; shared PCH/cache and per-TU variation prevent treating this as a bound. Qwen unknown.','completion_prediction':None,'adopted':False,'GO':False,'no_partial_binary_or_object_reuse':True,'qualification':'Mandatory H1 resource calibration only. Actual RTL/full geometry/rounding unchanged. No physical/token/rate credit.'}}
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True);p=OUT/'model.json';data=(json.dumps(census(),sort_keys=True,indent=2)+'\n').encode()
 with p.open('xb')as f:f.write(data)
 print(p)
