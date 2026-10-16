#!/usr/bin/env python3
"""HOST APIPE3/lockup proof on real ROWS/IKEY/RAW datapaths and boundary stimuli."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import numpy as np
import rtl_rom_host_ingest_bench as B
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261015)
cs={
 'ckv': B.C.case_rows(rng,'ckv',128,first=48),
 'window': B.C.case_rows(rng,'win',96,first=0),
 'ikey':B.C.case_ikey(rng,1024),
 'raw': B.C.case_raw(rng,300),
}
rec={'scope':'Component: real native ingest; only declared host input and external fabric expected image are reference supplied. Not die qualification.','sources':{str(x.relative_to(ROOT)):B.sha(x) for x in B.RTL+[B.TB]},'cases':{},'mutants':{}}
for name,c in cs.items():
 c['nb']=B.stream_nb(c['descs'])
 memw=B.C.pow2(max(c['exp'].size//32+1,1088));nd=B.C.pow2(len(c['descs']));npay=B.C.pow2(len(c['beats']))
 results={}
 for mode in ('apipe2','apipe3','mut_payload','mut_ap0'):
  out=a.out/(name+'_'+mode);out.mkdir(exist_ok=True)
  B.write_case(out,c,memw)
  pars=dict(MEMW=memw,ND=nd,NP=npay,HDMAX=16,KVHMAX=1,QKV_EN=0,RMW_EN=0,ENG_TRIM=1,APIPE=2 if mode=='apipe2' else 3,MUT=int(mode=='mut_payload'),HP=834,IP=834,CP=834)
  exe=out/'sim.vvp'
  defines=[] if mode=='apipe2' else ['-DOT_S81_HOST_PHASESAFE']
  if mode=='mut_ap0':defines+=['-DOT_ING_MUT_AP0SKIP']
  cmd=['iverilog','-g2012','-s','tb_rom_host_ingest','-o',str(exe.resolve()),*defines,*[f'-Ptb_rom_host_ingest.{k}={v}' for k,v in pars.items()],*map(str,B.RTL),str(B.TB)]
  cp=subprocess.run(cmd,capture_output=True,text=True);(out/'build.log').write_text(cp.stdout+cp.stderr)
  if cp.returncode:raise SystemExit('HOST_PHASE_INGEST BUILD_FAIL '+name+' '+mode)
  pa=dict(MAXCYC=400000)
  if name=='raw':pa.update(BOOTEND=1,BCOUNT=c['meta']['sectors'])
  result=B.run(exe.resolve(),out,len(c['descs']),len(c['beats']),**pa)
  results[mode]=result
  print(name,mode,json.dumps(result),flush=True)
  if mode in ('apipe2','apipe3') and not result['pass']:raise SystemExit('HOST_PHASE_INGEST FAIL '+name+' '+mode)
  if mode=='mut_payload' and result['pass']:raise SystemExit('HOST_PHASE_INGEST MUTANT_ESCAPED payload')
 rec['cases'][name]=results
rec['pass']=True
# AP0 skip is meaningful only for modes with address rows; RAW bypasses APIPE.
if not any(not rec['cases'][k]['mut_ap0']['pass'] for k in ('ckv','window','ikey')):raise SystemExit('HOST_PHASE_INGEST MUTANT_ESCAPED ap0')
(a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
print('HOST_PHASE_INGEST_GATE PASS actual ROWS IKEY RAW and payload/address mutants')
