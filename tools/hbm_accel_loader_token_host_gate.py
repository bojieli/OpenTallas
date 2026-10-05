#!/usr/bin/env python3
"""Acceptance8c: retained released fixture -> real host LOAD_VERIFY -> token.
No inference, golden generation, DUT preload, or full-checkpoint production.
"""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from hbm_accel_loader_installed_gate import sources
ROOT=Path(__file__).resolve().parents[1]

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def host_image(case,work,die,words):
 # Invert the pinned NS2 128-byte slice interleave: four p0 sectors, four p1.
 # Only format retained image bytes. CRC preserves bit0-first order per sector.
 table=[];reverse=[int(f'{b:08b}'[::-1],2) for b in range(256)]
 for b in range(256):
  c=b<<24
  for _ in range(8):c=((c<<1)&0xffffffff)^(0x04c11db7 if c&0x80000000 else 0)
  table.append(c)
 paths=[case/f'die{die}_p{s}.hex' for s in range(2)]
 crc=0xffffffff;out=work/f'host_die{die}.hex'
 with paths[0].open() as a,paths[1].open() as b,out.open('w') as o:
  for group in range(words//4):
   for f in [a,b]:
    for _ in range(4):
     line=f.readline().strip()
     if len(line)!=64:raise ValueError('retained partition sector must be256 bits')
     value=int(line,16);o.write(line+'\n')
     for byte in value.to_bytes(32,'little'):
      crc=((crc<<8)&0xffffffff)^table[(crc>>24)^reverse[byte]]
   if group%65536==0:print(f'HOST_FORMAT die{die} {group*8}/{words*2} sectors',flush=True)
  if a.readline() or b.readline():raise ValueError('retained partition depth mismatch')
 (work/f'host_die{die}.crc').write_text(f'{crc:08x}\n')
 return dict(retained={str(p):digest(p) for p in paths},host_sha256=digest(out),CRC=f'{crc:08x}',bytes=words*64)

def main():
 p=argparse.ArgumentParser();p.add_argument('--model',choices=['qwen','v41'],required=True);p.add_argument('--case',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--jobs',type=int,default=16);a=p.parse_args()
 if not 1<=a.jobs<=16:p.error('jobs1..16')
 a.work.mkdir(parents=True,exist_ok=False);case=a.work/'case';case.mkdir()
 params=dict(MEM_WORDS=65536 if a.model=='qwen' else 1<<21,HAS_DIV=int(a.model=='v41'),HAS_BD=int(a.model=='v41'))
 src=[s for s in sources() if s!='rtl/test/hbm_accel/tb_hbm_accel_loader_installed.sv']+['rtl/test/hbm_accel/tb_hbm_accel_loader_token_host.sv']
 rec=dict(source_pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),model=a.model,scope='retained reduced acceptance8c, real host image LOAD_VERIFY + actual code/command SRAM publication, no DUT preload',params=params,source_sha256={s:digest(ROOT/s) for s in src},retained_case=str(a.case),physical_qualified=False)
 rec['fixture_sha256']={}
 for f in ['tb_cfg.txt','expected.json']+[f'prog_d{d}_s{s}.hex' for d in range(2) for s in range(2)]+[f'cmd_d{d}.hex' for d in range(2)]:
  shutil.copy2(a.case/f,case/f);rec['fixture_sha256'][f]=digest(a.case/f)
 meta=json.loads((case/'expected.json').read_text());rec['expected_steps']=meta['steps']
 released=ROOT/f'results/rtl/hbm_system_rtl_20261003/{a.model}_e2e.json'
 if meta['steps']!=json.loads(released.read_text())['expected_steps']:raise ValueError('retained fixture differs from released acceptance golden')
 rec['released_record_sha256']=digest(released)
 rec['host_images']=[host_image(a.case,case,d,params['MEM_WORDS']) for d in range(2)]
 (a.work/'source_binding.json').write_text(json.dumps(rec,indent=2)+'\n')
 verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 cmd=[str(verilator),'--binary','--timing','-O2','-j',str(a.jobs),'--threads','8','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH','--x-assign','0','--x-initial','0','--top-module','tb_hbm_accel_loader_token_host','--Mdir',str(a.work/'obj')]+[f'-G{k}={v}' for k,v in params.items()]+[str(ROOT/s) for s in src]
 (a.work/'build_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
 # Owner's fleet target is load90..150 on the 128-core EPYC hosts. Formatting
 # uses one CPU; defer the parallel compiler while existing jobs exceed150.
 # This is admission, without a wall/runtime/address-space/file/RAM cap.
 while os.getloadavg()[0]>150:
  print(f'CPU_ADMISSION_WAIT load1={os.getloadavg()[0]:.2f} owner_fleet_target_max=150',flush=True);time.sleep(15)
 t=time.monotonic()
 with (a.work/'build.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 rec.update(build_rc=r.returncode,build_seconds=time.monotonic()-t,verdict='FAIL_BUILD')
 if r.returncode==0:
  t=time.monotonic()
  with (a.work/'run.log').open('w') as f:r=subprocess.run([str(a.work/'obj/Vtb_hbm_accel_loader_token_host'),'+DIR='+str(case)],cwd=case,stdout=f,stderr=subprocess.STDOUT)
  log=(a.work/'run.log').read_text();rec.update(run_rc=r.returncode,run_seconds=time.monotonic()-t,terminal_lines=[s for s in log.splitlines() if s.startswith(('HOST_IMAGE_VISIBLE','CODE_PUBLISHED','STEP','CQ','TB_GPU_HBM_SYSTEM','%Error','%Fatal'))],verdict='PASS' if r.returncode==0 and 'TB_GPU_HBM_SYSTEM PASS' in log else 'FAIL_FUNCTIONAL')
 (a.work/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['verdict'],flush=True);return 0 if rec['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
