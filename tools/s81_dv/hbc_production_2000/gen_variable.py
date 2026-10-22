#!/usr/bin/env python3
"""Real existing HBC1 schema, variable host word counts; component fixtures."""
import importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hbc_vectors',root/'hostctx_1021/gen_vectors.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
def field(w,lo,wd,v):return (w&~(((1<<wd)-1)<<lo))|(v<<lo)
for count in [33,515]:
 body=g.hbc_body(g.CTX);last=g.FIRST+16*(count-1);ks=last+32
 for lo,wd,v in [(272,10,count),(298,48,ks),(346,48,ks+96),(394,48,ks+32),(442,48,ks+64)]:body=field(body,lo,wd,v)
 crc=g.crc(body)
 rec=[(20,g.hbc_header(0,0,512,crc,g.CTX['programme'],24)),(24,body),(30,g.hbc_header(1,1,0,crc,g.CTX['programme'],30))]
 for i in range(count):
  data=int.from_bytes((0xf0000000|i).to_bytes(4,'little')*16,'little')
  edge=g.FIRST+16*i
  rec.extend([(edge-g.SEED+24,g.hbe_header(g.CTX,edge+4,g.crc(data))),(edge-g.SEED+28,data)])
 (out/f'w{count}.memh').write_text(''.join(f'{e:012x}{p:0128x}\n'for e,p in rec))
 (out/f'w{count}.json').write_text(json.dumps(dict(count=count,receiver_finish=ks+128,source='existingHBC1variable10bitwords',new_protocol=False),indent=2)+'\n')
 print(count,len(rec),ks+128)
