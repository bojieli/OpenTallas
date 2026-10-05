#!/usr/bin/env python3
"""Authorized host-only build in an exclusive directory. Never run numerical RTL."""
import hashlib,json,os,resource,shutil,subprocess,sys,time
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def audit(expected,work):
 pins={}
 for category,root in [('archives',expected['archive_root']),('sources',expected['source_root'])]:
  for name,want in expected[category].items():
   p=Path(root)/name;got=digest(p)
   if got!=want:raise ValueError('immutable original hash mismatch: '+str(p))
   pins[str(p)]=got
 for name,field in [('qwen_rom_rt_observed.cpp','prepared_host_sha256'),('qwen_rom_observer.hpp','observer_header_sha256')]:
  got=digest(work/name)
  if got!=expected[field]:raise ValueError('reviewed prepared input mismatch: '+name)
  pins[str(work/name)]=got
 compiler=Path(expected['compiler'])
 if digest(compiler)!=expected['compiler_sha256']:raise ValueError('fresh compiler identity changed')
 pins[str(compiler)]=digest(compiler)
 mem={l.split(':')[0]:l.split(':')[1].strip() for l in Path('/proc/meminfo').read_text().splitlines()}
 return {'pins':pins,'disk_free_B':shutil.disk_usage(work).free,'MemAvailable':mem['MemAvailable'],'CPU_affinity':sorted(os.sched_getaffinity(0)),'loadavg':os.getloadavg(),'compiler_version':subprocess.check_output([str(compiler),'--version'],text=True),'pid1220907_exists':Path('/proc/1220907').exists()}

def commands(expected,work):
 root=Path(expected['archive_root']);vr=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
 flags=['-std=c++20','-O2','-pthread']
 includes=['-I'+str(p) for p in [vr,vr/'vltstd',work,root/'coll',root/'die',root/'die/Vot_hdc_fmul',root/'die/Vot_hdc_qadd',root/'die/Vot_hdc_vstream_lane_a',root/'tile',Path(expected['source_root'])/'rtl/test/qwen_rom_runtime',Path(expected['source_root'])/'rtl/test/qwen_runtime']]
 defines=['GROUPS=6144','COUNTWIDTH=18','SWIDTH=64','SMAXB=11','TCUTL=7','NWSD=5','XVMD=1','TPD=4','CBANKS=5','SMINV=7','QROM_OBSERVER=1']
 compile_host=[expected['compiler']]+flags+['-D'+d for d in defines]+includes+['-c',str(work/'qwen_rom_rt_observed.cpp'),'-o',str(work/'host-observed.o')]
 runtime=[]
 for name in ['verilated','verilated_threads','verilated_dpi']:
  runtime.append([expected['compiler']]+flags+includes+['-c',str(vr/(name+'.cpp')),'-o',str(work/(name+'.o'))])
 archives=[root/p for p in ['coll/Vcoll__ALL.a','die/Vdie__ALL.a','die/Vot_hdc_fmul/libot_hdc_fmul.a','die/Vot_hdc_qadd/libot_hdc_qadd.a','die/Vot_hdc_vstream_lane_a/libot_hdc_vstream_lane_a.a','tile/Vtile__ALL.a']]
 link=[expected['compiler']]+flags+[str(work/'host-observed.o'),'-Wl,--start-group']+[str(p) for p in archives]+['-Wl,--end-group']+[str(work/(n+'.o')) for n in ['verilated','verilated_threads','verilated_dpi']]+['-o',str(work/'qwen_rom_rt_observed')]
 return [compile_host]+runtime+[link]

def main():
 work=Path(sys.argv[1]);expected=json.loads((work/'expected-inputs-r1.json').read_text())
 # No elapsed-time, CPU-time, address-space or file-size caps.
 for kind in [resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_AS]:resource.setrlimit(kind,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 record={'status':'FAIL_HOST_BUILD','supervisor_pid':os.getpid(),'source_commit':'9d7e70c2f4dc0a5f968d8eb149a314d7c5920039','lease':str(work),'numerical_run_launched':False,'start_epoch':time.time(),'commands':commands(expected,work)}
 try:
  record['before']=audit(expected,work)
  (work/'admission.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
  for index,cmd in enumerate(record['commands']):
   (work/'progress.json').write_text(json.dumps({'stage':index,'command':cmd,'supervisor_pid':os.getpid()},indent=2)+'\n')
   with (work/('stage%d.log'%index)).open('x') as log:
    proc=subprocess.Popen(['/usr/bin/time','-v']+cmd,stdout=log,stderr=subprocess.STDOUT)
    (work/'child.json').write_text(json.dumps({'stage':index,'pid':proc.pid,'command':cmd})+'\n')
    code=proc.wait()
   if code:raise RuntimeError('native stage%d exit%d'%(index,code))
  record['after']=audit(expected,work)
  if record['before']['pins']!=record['after']['pins']:raise ValueError('before/after input instability')
  record['status']='PASS_HOST_ONLY_RELINK_NOT_RUN'
  record['outputs']={str(p):{'sha256':digest(p),'bytes':p.stat().st_size} for p in [work/'host-observed.o',work/'qwen_rom_rt_observed']+[work/(n+'.o') for n in ['verilated','verilated_threads','verilated_dpi']]}
 except Exception as e:record['error']=str(e)
 record['end_epoch']=time.time()
 with (work/'terminal.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
 return 0 if record['status'].startswith('PASS_') else 1

if __name__=='__main__':sys.exit(main())
