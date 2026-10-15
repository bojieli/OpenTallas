#!/usr/bin/env python3
"""Source-only Engram ACK proof; old closed views do not bind rso variants."""
import argparse, hashlib, json, subprocess
from pathlib import Path
import engram_c_gate as G
ROOT=G.ROOT

def main():
    a=argparse.ArgumentParser(); a.add_argument('--out',type=Path,required=True); a.add_argument('--top',default='dsfd_engram_c_rso',choices=['dsfd_engram_c_rso','dsfd_engram_c_hl']); args=a.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    candidate=ROOT/'rtl/dsrom_sys/engram/rso_candidate'
    sources=G.SRC+sorted(p for p in candidate.glob('*.sv') if not p.name.startswith('tb_'))
    sources=sources+G.HL_EXTRA  # dsfd_engram_c_hl ACK relay dsfd_rly_1_EW
    tb=candidate/'tb_engram_rso.sv'
    if args.top!='dsfd_engram_c_rso':
        txt=tb.read_text().replace('dsfd_engram_c_rso dut(',args.top+' dut(')
        tb=args.out/('tb_engram_rso_'+args.top+'.sv'); tb.write_text(txt)
    receipt={'schema':'opentallas.s81.engram.rso_ack_gate.v1','top':args.top,'admission':False,'source_sha256':{str(p.relative_to(ROOT)) if ROOT in p.parents else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[tb]},'cases':{}}
    for case,flags in [('exact',[]),('missing_pb2',['-DOT_ENGC_RSO_MUT_MISSING_PB2']),('missing_fifo_rd',['-DOT_ENGC_RSO_MUT_MISSING_FIFO_RD'])]:
        obj=args.out/('obj_'+case)
        cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_engram_rso','-j','4','-Mdir',str(obj),*flags,*map(str,sources),str(tb)]
        with (args.out/(case+'_build.log')).open('w') as f: build=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        if build.returncode:
            receipt['cases'][case]={'classification':'BUILD_FAIL','exit':build.returncode}; break
        with (args.out/(case+'_run.log')).open('w') as f: run=subprocess.run([str(obj/'Vtb_engram_rso')],stdout=f,stderr=subprocess.STDOUT,timeout=120)
        log=(args.out/(case+'_run.log')).read_text()
        passed=run.returncode==0 and 'ENGRAM_RSO_ACK PASS:' in log
        expected_fault={'missing_pb2':'ACK FAIL: high with PB2 final release held low','missing_fifo_rd':'ACK FAIL: high with IO FIFO final release held low'}.get(case)
        caught=run.returncode!=0 and expected_fault is not None and expected_fault in log
        receipt['cases'][case]={'exit':run.returncode,'classification':'PASS' if passed else ('FUNCTIONAL_FAIL_CAUGHT' if caught else 'UNEXPECTED_FAIL'),'log':log}
        print(case,receipt['cases'][case]['classification'],flush=True)
    receipt['verdict']='PASS' if receipt['cases'].get('exact',{}).get('classification')=='PASS' and all(receipt['cases'].get(c,{}).get('classification')=='FUNCTIONAL_FAIL_CAUGHT' for c in ['missing_pb2','missing_fifo_rd']) else 'FAIL'
    (args.out/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('ENGRAM_RSO_ACK_GATE',receipt['verdict'],flush=True)
    return 0 if receipt['verdict']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
