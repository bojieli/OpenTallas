#!/usr/bin/env python3
"""Only the NEW registered-head async system options, using existing images/results."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import re
import subprocess
import time
import qwen_rom_sys_async_campaign as C

# Same qualified module bytes, selected additively in the async namespace.
_HEADREG_SOURCE = {
    "rtl/qwen_sys/async/ot_qwen_rom_sys_top.sv": "rtl/qwen_sys/async/headreg/ot_qwen_rom_sys_top.sv",
    "rtl/qwen_sys/async/ot_qwen_sys_die.sv": "rtl/qwen_sys/async/headreg/ot_qwen_sys_die.sv",
    "rtl/test/qwen_sys/async/tb_qwen_rom_sys.sv": "rtl/test/qwen_sys/async/headreg/tb_qwen_rom_sys.sv",
}
C.SYS_FILES = [_HEADREG_SOURCE.get(f, f) for f in C.SYS_FILES] + ["rtl/rom/ot_rom_oneshot_headreg.sv"]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--async-img',type=Path,required=True)
    ap.add_argument('--reference',type=Path,required=True,help='collected async_result.json; baseline is never rerun')
    ap.add_argument('--admit',type=Path,required=True)
    ap.add_argument('--expected-peak-gb',type=int,default=8)
    ap.add_argument('--jobs',type=int,default=4)
    a=ap.parse_args()
    for name in ('work','out','async_img','reference','admit'): setattr(a,name,getattr(a,name).resolve())
    if a.out.exists(): ap.error('immutable output exists')
    if not (a.async_img/'expect.json').exists(): ap.error('existing images required')
    baseline=json.loads(a.reference.read_text())
    if baseline['status']!='pass': ap.error('reference async gate must pass')
    a.out.mkdir(parents=True);a.work.mkdir(parents=True,exist_ok=True)
    rc,out,_=C.sh(['python3','tools/qwen_rom_sys_core2clk_emit.py','--out',C.ROOT/'build/qwen_sys'])
    if rc: raise RuntimeError(out)
    sources=set(C.SYS_FILES+[C.HARNESS2,'rtl/hdc/ot_hdc_isa.svh','tools/qwen_rom_sys_headreg_gate.py','tools/qwen_rom_sys_async_campaign.py'])
    pins={p:C.sha(C.ROOT/p) for p in sorted(sources)}
    images={p.name:C.sha(p) for p in sorted(a.async_img.glob('*.hex'))}
    record={'schema':'opentallas.qwen-headreg-system-gate.v1','status':'pending','source_sha256':pins,
            'image_sha256':images,'reference_sha256':C.sha(a.reference),
            'claim':'Reduced real-program system with async sequencer; no fullshape/SS-FF adoption.', 'runs':{}}
    (a.out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    binaries={}
    # Admission wraps each actual build; one build at a time, using the campaign's qualified quoting.
    for name,cdc,pf in [('c0p0ah',0,0),('c1p1ah',1,1)]:
        extra=[f'-GME_CDC={cdc}',f'-GKV_PREFETCH={pf}','-GSEQ_ASYNC=1','-GCOLL_HEADREG=1']
        cmd=['python3','-c',
             'import sys; from pathlib import Path; sys.path.insert(0,"tools"); import qwen_rom_sys_headreg_gate as g; c=g.C; '
             'c.vbuild("tb_qwen_rom_sys",c.SYS_FILES,Path(sys.argv[1]),sys.argv[3:],int(sys.argv[2]),c.HARNESS2)',
             str(a.work/('obj_'+name)),str(a.jobs),*extra]
        rc,out,wall=C.sh([a.admit,str(a.expected_peak_gb),'--',*cmd])
        (a.out/('build_'+name+'.log')).write_text(out)
        record.setdefault('builds',{})[name]={'returncode':rc,'wall_s':wall,'parameters':extra}
        if rc:
            record['status']='fail';(a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n');return 1
        binaries[name]=a.work/('obj_'+name)/'Vtb_qwen_rom_sys'
    cases=[('c0p0ah_u1','c0p0ah','c0p0a_u1',['+USERS=1']),
           ('c1p1ah_u1','c1p1ah','c1p1a_u1',['+USERS=1']),
           ('c1p1ah_u2_flip97','c1p1ah','c1p1a_u2_flip97',['+USERS=2','+FLIP=97']),
           ('c1p1ah_u1_fphase1','c1p1ah','c1p1a_u1_fphase1',['+USERS=1','+FPHASE=1'])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending={n:(ref,pool.submit(C.run,binaries[v],[f'+DIR={a.async_img}','+CLK='+('split' if v=='c1p1ah' else 'slow'),*extras],a.out/(n+'.log')))
                 for n,v,ref,extras in cases}
        for n,(ref,f) in pending.items():
            r=f.result()
            current=next((x for x in r['summary'] if x.startswith('SYS ')),'')
            old=next(x for x in baseline['runs'][ref]['summary'] if x.startswith('SYS '))
            match=re.search(r' cycles=(\d+)',current)
            r['reference_run']=ref
            if match:
                r['cycles']=int(match[1]);r['reference_cycles']=int(re.search(r' cycles=(\d+)',old)[1]);r['added_cycles']=r['cycles']-r['reference_cycles']
            record['runs'][n]=r
    record['source_stable']=pins=={p:C.sha(C.ROOT/p) for p in pins}
    record['images_stable']=images=={p.name:C.sha(p) for p in sorted(a.async_img.glob('*.hex'))}
    record['status']='pass' if all(r['pass'] and r['returncode']==0 for r in record['runs'].values()) and record['source_stable'] and record['images_stable'] else 'fail'
    (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'status':record['status'],'cycles':{n:r.get('added_cycles') for n,r in record['runs'].items()}}),flush=True)
    return int(record['status']!='pass')

if __name__=='__main__': raise SystemExit(main())
