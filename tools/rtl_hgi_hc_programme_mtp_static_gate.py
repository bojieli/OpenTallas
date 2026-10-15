#!/usr/bin/env python3
import json,hashlib,subprocess
from pathlib import Path
from lower_hbm_hc_mtp_static_calendar import lower
ROOT=Path(__file__).resolve().parents[1]
def main():
    run=ROOT/'run_hc_programme_mtp';run.mkdir(exist_ok=True)
    images={}
    for npos in (6,8):
        for early in (False,True):
            name=f'n{npos}_e{int(early)}'
            words,meta=lower('row',first_consumer_cycle=2053,sink_divisor=7,sink_phase=0,row=23,slot=1,clear=True,npos=npos,early=early)
            (run/f'{name}.mem').write_text(''.join(f'{w:064x}\n' for w in words))
            images[name]={'words':len(words),'metadata':meta}
    for position in (0,7):
        name=f'tail_position{position}'
        words,meta=lower('tail',first_consumer_cycle=2053,sink_divisor=7,sink_phase=0,tail_position=position)
        (run/f'{name}.mem').write_text(''.join(f'{w:064x}\n' for w in words))
        images[name]={'words':len(words),'metadata':meta}
    files=['rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_programme_mtp_static.sv',
        'rtl/hbm_accel/generic/peers/ot_hgi_sfu_program_stripe_static.sv',
        'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
        'rtl/test/tb_hgi_hc_programme_mtp_static.sv','rtl/test/hgi_hc_programme_mtp_static_harness.cpp']
    pins=files+['tools/lower_hbm_hc_mtp_static_calendar.py','tools/rtl_hgi_hc_programme_mtp_static_gate.py']
    receipt={'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},'images':images,
        'scope':'real two-page programme1024x256 macros and51HCcontrol pins, not arithmetic/wholelayer qualification'}
    with (run/'build.log').open('w') as log:
        subprocess.run(['verilator','--cc','--exe','--build','-j','1','-O1','-Wno-fatal','-Wno-WIDTH',
            '-Wno-TIMESCALEMOD','--top-module','tb_hgi_hc_programme_mtp_static','-Mdir',str(run/'obj'),*[str(ROOT/f) for f in files]],cwd=run,stdout=log,stderr=subprocess.STDOUT,check=True)
    cases=[(k,[f'+IMAGE={k}.mem',f'+WORDS={v["words"]}']) for k,v in images.items()]
    cases.append(('mutant',['+IMAGE=n8_e1.mem',f'+WORDS={images["n8_e1"]["words"]}','+MUTANT']))
    for name,args in cases:
        p=subprocess.run([str(run/'obj/Vtb_hgi_hc_programme_mtp_static'),*args],cwd=run,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (run/f'{name}.log').write_text(p.stdout);print(name,p.returncode,p.stdout[-1000:],flush=True)
        receipt[name]={'exit_code':p.returncode,'log_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if name!='mutant' and p.returncode:raise SystemExit('positive gate failed')
        if name=='mutant' and not p.returncode:raise SystemExit('mutant escaped')
if __name__=='__main__':main()
