#!/usr/bin/env python3
"""Minimum DMA-front exactness/stack-local ownership gate; never claims HBM90%."""
import argparse, hashlib, json, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=R/'rtl/hbm_accel/generic/peers'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--verilator',default='verilator')
    p.add_argument('--jobs',type=int,default=8)
    p.add_argument('--admit',type=Path,help='optional host measured-headroom guard')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    raw=(D/'ot_hgi_dma_front.sv').read_text()
    before='tg_dsec[tag_slot(i/NL,in[267:264])]'
    assert raw.count(before)==1
    alias=a.out/'tag_alias.sv';alias.write_text(raw.replace(before,'tg_dsec[tag_slot(0,in[267:264])]'))
    prod=dict(LDEPTH=256,DATA_HOPS=80,CREDIT_HOPS=80,RESPONSE_LATENCY=104,SERVICE_SLOTS=8)
    cases=[('default',{},False,False,True),
        ('legacy_bandwidth',dict(prod,BW_SCOPE=1,STACK_LOCAL_TAGS=0),True,False,True),
        ('stacklocal_full',dict(prod,BW_SCOPE=1,STACK_LOCAL_TAGS=1),False,False,True),
        ('BF16_mirror',dict(prod,BW_SCOPE=1,STACK_LOCAL_TAGS=1,MUT=1),True,False,True),
        ('stack_alias',dict(prod,BW_SCOPE=1,STACK_LOCAL_TAGS=1),True,True,True),
        ('stacklocal_random',dict(prod,BW_SCOPE=2,STACK_LOCAL_TAGS=1),False,False,False),
        ('early_tag_random',dict(prod,BW_SCOPE=2,STACK_LOCAL_TAGS=1,MUT=2),True,False,False)]
    results=[]
    for name,params,negative,is_alias,full in cases:
        out=a.out/name;out.mkdir()
        src=alias if is_alias else D/'ot_hgi_dma_front.sv';bench=D/'tb_hgi_dma_front.sv'
        cmd=[a.verilator,'--binary','--timing','-Wno-fatal','--top-module','tb_hgi_dma_front',
             '--Mdir',str((out/'vlt').resolve()),'-j',str(a.jobs),
             *[f'-G{k}={v}' for k,v in params.items()],str(src.resolve()),str(bench)]
        if a.admit:cmd=[str(a.admit),'8','--',*cmd] # measured prior build57.7MiB/run1020MiB, eight compile workers
        with (out/'build.log').open('w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        result=dict(name=name,parameters=params,expected_negative=negative,full_source=full,compile_exit=cp.returncode,
            source_sha256={s.name:hashlib.sha256(s.read_bytes()).hexdigest()for s in(src,bench)})
        if cp.returncode==0:
            with (out/'run.log').open('w')as f:
                sim=subprocess.run([str((out/'vlt/Vtb_hgi_dma_front').resolve()),'+DMA_PROFILE',*(['+FULL']if full else[])],stdout=f,stderr=subprocess.STDOUT)
            text=(out/'run.log').read_text()
            exact=sim.returncode==0 and 'PASS HGI_DMA_FRONT'in text and 'FAIL'not in text
            failure=sim.returncode!=0 or 'FAIL'in text
            result.update(sim_exit=sim.returncode,exact_pass=exact,negative_detected=failure,
                          passed=failure if negative else exact)
        else:result['passed']=False
        results.append(result)
        (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    receipt=dict(verdict='PASS_FRONT_STACKLOCAL_ONLY'if all(r['passed']for r in results)else'FAIL',cases=results,
        physical_admitted=False,HBM90pct=False,VM_ABI_words=262144,
        limitations=['only current 1024B/cycle lane/VM capacity; equals32.34pct of sustained3800GB/s HBM at1.2GHz',
                     'source delay104 and finite8-slot service queue are modeled; parent separately qualifies actual service',
                     'cold load latency is reported separately from payload span, never removed from token accounting',
                     'no routed views, floorplan fit or integrated DMA service/VM qualification'])
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['verdict']);return 0 if receipt['verdict']=='PASS_FRONT_STACKLOCAL_ONLY'else 1
if __name__=='__main__':raise SystemExit(main())
