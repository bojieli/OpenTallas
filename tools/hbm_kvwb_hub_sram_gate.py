"""EPYC2 admitted minimum fullhub SRAM gate, independent address/data oracle.

Only hub and timed Gray-counter respondents; no array, service, or HBM stack.
Fresh source bundle and output paths required. Owner forbids local builds.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_kvwb_die_bench as B
TOP='tb_hbm_kvwb_hub_sram'
SOURCES=['rtl/common/ot_secded.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
 'rtl/hbm_accel/service/ot_hbm_accel_dskv_shadow_sram.sv',
 'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_sram.sv',
 'rtl/hbm_accel/service/ot_hbm_kport_map.sv','rtl/hbm_accel/service/ot_hbm_kvwb_hub_sram.sv',
 'rtl/test/hbm_accel/tb_hbm_kvwb_hub_sram.sv']
PINS=SOURCES+['rtl/common/ot_secded_cols.svh','tools/hbm_kvwb_hub_sram_gate.py',
 'tools/hbm_kvwb_die_bench.py','tools/hbm_accel_dskv_wb.py']
def plan():
 rng=random.Random(20261008)
 data=lambda n:bytes(rng.randrange(256) for _ in range(n))
 p=B.Plan(0)
 for slot in range(8):p.shadow_load(slot,data(544))
 p.window(0,20,data(528));p.ckv(0,20,data(288))
 for slot,L in enumerate(B.SRC_LAYERS):
  for i in range(8):p.key(i*(2 if B.RATIO[L]==2 else 1),L,data(68))
 return p

def check(txt,p):
 problems=[];got=Counter()
 for m in re.finditer(r'^W (\d+) (\d+) (\d+) ([0-9a-f]+)$',txt,re.M):
  st,pc,addr=int(m[1]),int(m[2]),int(m[3]);dpc,bk,rw,cl=B.decode(addr)
  if dpc!=pc:problems.append('PC decode mismatch')
  got[(st,pc,bk,rw,cl,int(m[4],16).to_bytes(32,'little'))]+=1
 want=Counter(p.writes)
 if got!=want:problems.append(f'writes missing={sum((want-got).values())} extra={sum((got-want).values())}')
 final={(st,B.kaddr(pc,bk,rw,cl)):b for st,pc,bk,rw,cl,b in p.writes}
 seen={}
 for m in re.finditer(r'^M (\d+) (\d+) ([0-9a-f]+)$',txt,re.M):
  key=int(m[1]),int(m[2])
  if key in seen:problems.append('duplicate final peek')
  seen[key]=int(m[3],16).to_bytes(32,'little')
 if seen!=final:problems.append('final bytes at first fence differ or incomplete')
 f=re.search(r'^F (.*)$',txt,re.M)
 metrics=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',f[1])) if f else {}
 if any(metrics.get(k)!=len(p.writes) for k in ('issued','acked','received','completed','expected')):problems.append('fence precedes all source-owned completions')
 if metrics.get('fence_ok')!=1 or metrics.get('map_fault')!=0:problems.append('fence or fault status')
 if metrics.get('producer_stalls',0)<=0 or metrics.get('sector_stalls',0)<=0 or metrics.get('shadow_wait',0)<=0:problems.append('missing credit or shadow handshake coverage')
 if metrics.get('shadow_accepted')!=8:problems.append('missing preload handshakes')
 if metrics.get('rows')!=len(p.rows) or 'END' not in txt:problems.append('incomplete execution')
 return dict(verdict='FAIL' if problems else 'PASS',problems=problems,metrics=metrics)

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--work',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--source-commit',required=True);ap.add_argument('--peak-gb',type=float,required=True)
 ap.add_argument('--jobs',type=int,default=2)
 ap.add_argument('--verilator',default=os.environ.get('VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')))
 a=ap.parse_args()
 if os.uname().nodename!='climbing-locust':raise SystemExit('EPYC2 only; owner forbids local simulation/build')
 if a.work.exists() or a.out.exists():raise SystemExit('fresh immutable work/output required')
 if a.peak_gb<=0 or a.jobs<=0:raise SystemExit('positive admission reservation/jobs required')
 pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in PINS}
 a.work.mkdir(parents=True);a.out.parent.mkdir(parents=True,exist_ok=True)
 p=plan();rec=dict(schema='opentallas.hbm_accel.kvwb_hub_sram_gate.v1',source_commit=a.source_commit,input_sha256=pins,
 host=os.uname().nodename,admission_peak_gb=a.peak_gb,admission_guard='/srv/opentallas-scratch/admit.sh',
 scope='full hub plus timed Gray respondents; no array/service/HBM stack',clock_ps=833,respondent_clock_ps=1024,
 coverage=dict(shadow_slots=8,shadow_sectors_per_slot=17,key_positions_per_slot=8,key_sector_spans=[3]*64,window_rows=1,ckv_rows=1),cases=[],verdict='FAIL')
 for mut in (0,1):
  obj=a.work/f'obj{mut}'
  cmd=['/srv/opentallas-scratch/admit.sh',str(a.peak_gb),'--','/usr/bin/time','-v',a.verilator,'--binary','--timing','-Wno-fatal','-j',str(a.jobs),'-O2','--top-module',TOP,'--Mdir',str(obj),'-I'+str(ROOT/'rtl/common'),f'-GMUT={mut}']+[str(ROOT/s) for s in SOURCES]
  with (a.work/f'build{mut}.log').open('w') as log:b=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  print(f'ELAB_BUILD mut={mut} returncode={b.returncode}',flush=True)
  if b.returncode:rec['cases'].append(dict(mut=mut,verdict='BUILD_FAIL'));continue
  for early in ((0,1) if mut==0 else (0,)):
   run_dir=a.work/f'case{mut}_{early}';run_dir.mkdir()
   (run_dir/'rows.txt').write_text(''.join(f'{k} {s} {r} {pos} {sh} {B.hx(data)}\n' for k,s,r,pos,sh,data in p.rows))
   final={(st,B.kaddr(pc,bk,rw,cl)):data for st,pc,bk,rw,cl,data in p.writes}
   (run_dir/'peek.txt').write_text(''.join(f'{st} {addr}\n' for st,addr in sorted(final)))
   cmd=['/srv/opentallas-scratch/admit.sh',str(a.peak_gb),'--',str(obj/('V'+TOP)),f'+rows={run_dir}/rows.txt',f'+peek={run_dir}/peek.txt',f'+out={run_dir}/out.txt',f'+expected={len(p.writes)}',f'+early={early}']
   with (run_dir/'sim.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
   row=check((run_dir/'out.txt').read_text() if (run_dir/'out.txt').exists() else '',p)
   row.update(mut=mut,early=early,returncode=r.returncode);rec['cases'].append(row)
 rec['input_unchanged']=pins=={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in PINS}
 cases=rec['cases']
 rec['verdict']='PASS' if len(cases)==3 and cases[0]['verdict']=='PASS' and all(c['verdict']=='FAIL' for c in cases[1:]) and rec['input_unchanged'] else 'FAIL'
 with a.out.open('x') as f:json.dump(rec,f,indent=2);f.write('\n')
 print(json.dumps(rec,indent=2),flush=True)
 return rec['verdict']!='PASS'
if __name__=='__main__':sys.exit(main())
