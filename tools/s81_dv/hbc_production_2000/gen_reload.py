#!/usr/bin/env python3
"""Two genuine LOAD/body/COMMIT contexts on independently named boot/epoch dates."""
import importlib.util,json,sys
from pathlib import Path
sp=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'hostctx_1021/gen_vectors.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
def field(w,lo,wd,v):return(w&~(((1<<wd)-1)<<lo))|(v<<lo)
def context(seq,header,mode):
 count=33 if seq==0 else 515;seed=1000 if seq==0 else 10000;first=seed+100
 ctx=dict(g.CTX)
 if seq:ctx.update(tid=38,user=1,position=1048576,token=16755,epoch=0x2021,programme=g.CTX['programme']^0x8000000000000000)
 last=first+16*(count-1);ks=last+32;body=g.hbc_body(ctx)
 for lo,wd,v in [(164,48,seed),(212,48,first),(272,10,count),(298,48,ks),(346,48,ks+96),(394,48,ks+32),(442,48,ks+64)]:body=field(body,lo,wd,v)
 crc=g.crc(body);bodydate=header+4;commit=header+10
 if seq and mode==2:bodydate+=10000
 records=[(header,g.hbc_header(0,0,512,crc,ctx['programme'],bodydate)),(header+4,body^(1<<100) if seq and mode==3 else body),(commit,g.hbc_header(1,1,0,crc,ctx['programme'],commit))]
 for i in range(count):
  payload=int.from_bytes((0xf0000000|(seq<<24)|i).to_bytes(4,'little')*16,'little');edge=first+16*i
  records.extend([(edge-seed+header+4,g.hbe_header(ctx,edge+4,g.crc(payload))),(edge-seed+header+8,payload)])
 return records
for mode in range(5):
 h=700 if mode==1 else 800
 rec=context(0,20,mode)+context(1,h,mode);rec.sort()
 assert len({e for e,p in rec})==len(rec)
 (out/f'r{mode}.memh').write_text(''.join(f'{e:012x}{p:0128x}\n'for e,p in rec))
(out/'contract.json').write_text(json.dumps(dict(first=dict(header_boot=20,body_boot=24,commit_boot=30,seed_receiver=1000,PREV_receiver=1740),second=dict(header_boot=800,body_boot=804,commit_boot=810,seed_receiver=10000),guard='old receiver>=PREV_input+3 AND actualbusyfalse; BOOT dates never compared as receiver dates',modes={0:'positive33then515',1:'earlyreload',2:'counterdomaincast',3:'badCRC',4:'actualbusy'}),indent=2)+'\n')
