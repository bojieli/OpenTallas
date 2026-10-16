#!/usr/bin/env python3
"""Actual RTL positive and two hardware timing mutants; image generated independently."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from controller_calendar_image import Run,compile_image
ROOT=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('out',type=Path);x=a.parse_args();out=x.out.resolve();out.mkdir(parents=True,exist_ok=True)
# Full 256-sector K and 256-sector V traffic plus distinct static read/write
# reservations. This image is a component fixed-edge witness, not permission
# to claim these artificial offsets form a complete JEDEC/write schedule.
runs=[Run(10,command=(256<<20)|1),Run(80,command=(1<<31)|1),Run(120,256,8,2,mask=1),
      Run(900,command=(512<<33)|(768<<20)|1),Run(960,command=(1<<31)|1),Run(1000,256,8,3,mask=1),
      Run(1500,mask=2,static_read=True),Run(1650,mask=4)]
z=compile_image(runs,deadline=1800)
(out/'image.hex').write_text(''.join(f'{w:032x}\n' for w in z['words']))
expected=[0]*4096
for t,e in z['events'].items():expected[t]=e['command']|(e['mask']<<43)
for t,e in z['events'].items():
 if e['mask']==1 or e['static_read']:expected[t+27]|=1<<46
(out/'expect.hex').write_text(''.join(f'{w:016x}\n' for w in expected))
files=['rtl/qwen_sys/static_kv_20261014/qkd_controller_hbm_calendar.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_calendar.sv','rtl/test/qwen_static_kv/tb_controller_hbm_calendar.sv']
verilator=os.environ.get('VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
result=[]
for m in (0,1,2):
 obj=out/f'obj{m}'
 cmd=[verilator,'--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_controller_hbm_calendar',f'-GMUT={m}','--Mdir',str(obj)]+[str(ROOT/f) for f in files]
 with (out/f'build{m}.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 p=subprocess.run([str(obj/'Vtb_controller_hbm_calendar'),f'+IMAGE={out}/image.hex',f'+EXPECT={out}/expect.hex'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/f'run{m}.log').write_text(p.stdout);result.append(dict(mutant=m,exit=p.returncode,output=p.stdout[-1000:]))
 if m==0:assert p.returncode==0 and 'PASS controller calendar'in p.stdout,p.stdout
 else:assert p.returncode!=0 and 'FAIL controller calendar'in p.stdout,p.stdout
# Independent structural invalid-image controls.
for bad in ([Run(1)],[Run(4),Run(4)],[Run(4,mask=3)],[Run(65535,count=2)],[Run(10+i)for i in range(17)]):
 try:compile_image(bad)
 except ValueError:pass
 else:raise AssertionError('invalid image accepted')
receipt=dict(scope='compressed controller producer component, 36 fixed frame repeats; not full memory/native layer',source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files},storage_bits=z['storage_bits'],events_per_frame=len(z['events']),results=result,invalid_image_controls=5,native_full_layer=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
