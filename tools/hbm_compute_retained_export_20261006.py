#!/usr/bin/env python3
"""Extract actual retained compute macros; no synthesis, P&R or proof replay.

Run sequentially on EPYC2 only. Fresh CPU fit is required even for a small
admission declaration. Every source ODB/SPEF/SDC is checked against the adopted
corner record. Interface extraction removes IO false paths; it is not another
signoff verdict. Source route constraints and evidence remain immutable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
LIBS = {
 'ss': ['AO_RVT_SS_nldm_211120.lib.gz','INVBUF_RVT_SS_nldm_220122.lib.gz','OA_RVT_SS_nldm_211120.lib.gz','SEQ_RVT_SS_nldm_220123.lib','SIMPLE_RVT_SS_nldm_211120.lib.gz'],
 'ff': ['AO_RVT_FF_nldm_211120.lib.gz','INVBUF_RVT_FF_nldm_220122.lib.gz','OA_RVT_FF_nldm_211120.lib.gz','SEQ_RVT_FF_nldm_220123.lib','SIMPLE_RVT_FF_nldm_211120.lib.gz']}
IMAGE = 'openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'


def sha(path):
 h = hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()


def dump(path, data):
 Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def cpu_sample():
 v=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
 return sum(v[:8]),v[3]+v[4]


def capacity(out, phase):
 t0,i0=cpu_sample();time.sleep(.5);t1,i1=cpu_sample()
 idle_cpus=(i1-i0)/(t1-t0)*os.cpu_count()
 m = dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
 stat = os.statvfs(out)
 d = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),phase=phase,
          host=socket.gethostname(),cpus=os.cpu_count(),load1=os.getloadavg()[0],
          available_gib=int(m['MemAvailable'].split()[0])/1024**2,
          disk_free_gib=stat.f_bavail*stat.f_frsize/2**30)
 d['idle_cpus']=idle_cpus
 d['required_idle_cpus']=1
 d['cpu_fit'] = d['load1'] < d['cpus'] and idle_cpus >= 1
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(d)+'\n')
 return d


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--inputs',type=Path,required=True)
 ap.add_argument('--name',required=True)
 ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--admitted',action='store_true',help='internal: after unchanged admit.sh')
 a=ap.parse_args()
 if not Path('/srv/opentallas-scratch/admit.sh').is_file():
  ap.error('EPYC2 execution only; no local export fallback')
 rows=json.loads(a.inputs.read_text())['rows']; r=next(x for x in rows if x['name']==a.name)
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if (out/'export.json').exists():ap.error('completed/failure evidence already exists; choose a new attempt')
 phase='post_admission' if a.admitted else 'pre_admission'
 c=capacity(out,phase)
 if not c['cpu_fit']:
  print('CPU_CAPACITY_BLOCKED '+json.dumps(c),flush=True);return 75
 # Reserve an output inventory allowance from the actual retained source sizes,
 # not a file-size cap: input ODB+SPEF+netlist plus room for all extracted views.
 root=Path(r['route_root']);base=next((root/'work/orfs/results/asap7').glob('*/base'))
 required_disk=sum((base/('6_final.'+x)).stat().st_size for x in ['odb','spef','v'])*4
 if c['disk_free_gib']*2**30 < required_disk:
  print('DISK_CAPACITY_BLOCKED',flush=True);return 75
 if not a.admitted:
  cmd=['/srv/opentallas-scratch/admit.sh','12','--',sys.executable,str(Path(__file__).resolve()),
       '--inputs',str(a.inputs.resolve()),'--name',a.name,'--out',str(out),'--admitted']
  return subprocess.call(cmd)
 for ext, expected in r['hashes'].items():
  actual=sha(base/('6_final.'+ext))
  if actual!=expected:raise ValueError(f'{ext} source mismatch {actual} != {expected}')
 constraint=root/'physical_artifacts/constraint.sdc'
 original=constraint.read_text()
 interface='\n'.join(line for line in original.splitlines() if not line.strip().startswith('set_false_path'))+'\n'
 if not re.search(r'set clk_period 833\b',interface):raise ValueError('actual period not adopted 833 ps')
 if 'set_clock_uncertainty -setup 60' not in interface or 'set_clock_uncertainty -hold 25' not in interface:
  raise ValueError('actual uncertainty differs from SS60FF25')
 (out/'interface.sdc').write_text(interface)
 (out/'source_constraint.sdc').write_text(original)
 corner=json.loads((root/'corner_sta.json').read_text())
 if not corner['closes_signoff']:raise ValueError('retained source not closed')
 rec=dict(schema='opentallas.hbm.compute.retained_export.v1',name=a.name,
          source=r,image=IMAGE,script_sha256=sha(__file__),corners={},
          source_constraint_sha256=sha(constraint),interface_sdc_sha256=sha(out/'interface.sdc'),
          interface_scope='Actual extracted port/clock arcs with source IO falsepaths removed; original internal signoff reused, parent unqualified',
          source_signoff_reused=True,parent_qualified=False,threads=1)
 dump(out/'source_corner_sta.json',json.loads((root/'corner_sta.json').read_text(),parse_constant=lambda _:None))
 for cc in ['ss','ff']:
  if not capacity(out,'before_'+cc)['cpu_fit']:
   rec['status']='CPU_CAPACITY_BLOCKED';dump(out/'partial.json',rec);return 75
  libs='\n'.join(f'read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_{x}' for x in LIBS[cc])
  lef=f'write_abstract_lef /out/{a.name}.lef\n' if cc=='ss' else ''
  pins=''
  if cc=='ss':
   pins='''set fp [open /out/pins.tsv w]
puts $fp "pin\tdirection\tsignal_type\tlayer\txmin_um\tymin_um\txmax_um\tymax_um"
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
puts "OT_DBU $dbu"
foreach bt [$block getBTerms] {
  foreach bp [$bt getBPins] {
    foreach box [$bp getBoxes] {
      puts $fp [join [list [$bt getName] [$bt getIoType] [$bt getSigType] [[$box getTechLayer] getName] [expr {double([$box xMin])/$dbu}] [expr {double([$box yMin])/$dbu}] [expr {double([$box xMax])/$dbu}] [expr {double([$box yMax])/$dbu}]] "\\t"]
    }
  }
}
close $fp
'''
  tcl=f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{libs}
read_db /base/6_final.odb
read_sdc /out/interface.sdc
read_spef /base/6_final.spef
set_propagated_clock [all_clocks]
report_units
report_clock_properties [all_clocks]
write_timing_model -library_name {a.name}_{cc} /out/{a.name}_{cc}.lib
{lef}{pins}puts "OT_EXPORT_DONE"
exit
'''
  (out/f'export_{cc}.tcl').write_text(tcl)
  cmd=['docker','run','--rm','--cpus','1','-e','OMP_NUM_THREADS=1',
       '-v',str(base)+':/base:ro','-v',str(out)+':/out',IMAGE,
       '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-threads','1','-exit',f'/out/export_{cc}.tcl']
  with (out/f'export_{cc}.log').open('w') as f:
   ret=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
  log=(out/f'export_{cc}.log').read_text()
  rec['corners'][cc]=dict(returncode=ret,done='OT_EXPORT_DONE' in log,command=cmd,
       post_extract_capacity=capacity(out,'after_'+cc))
  if ret or 'OT_EXPORT_DONE' not in log:
   rec['status']='EXTRACTION_FAILED';dump(out/'export.json',rec);return 1
 rec['files']={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.lef','.lib','.sdc','.tsv']}
 rec['post_export_capacity']=capacity(out,'post_export')
 rec['status']='EXPORTED_REAL_RETAINED_LEAF'
 dump(out/'export.json',rec)
 print(json.dumps(rec),flush=True)
 return 0


if __name__=='__main__':sys.exit(main())
