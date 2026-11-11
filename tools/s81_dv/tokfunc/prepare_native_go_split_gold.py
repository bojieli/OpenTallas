#!/usr/bin/env python3
"""S81-PLAN-1 D (11-10): independent checkpoint gold for the gb_split GO/TAG qualification bench (tb_native_go_split.sv).

Same arithmetic as prepare_native_go_pair_gold.py (checkpoint wq_a codes / scales / activation, OPTAG1 first-tag authority);
the rows come from the regenerated field phase 0 (xs_place.py frame, its own row_index) instead of the 11-01 field's literal
224..227, and nseg from that phase."""
from pathlib import Path
import argparse,json,hashlib,os,sys

def main():
 p=argparse.ArgumentParser()
 for key in ('source','field','fixture','out'):p.add_argument('--'+key,required=True,type=Path)
 a=p.parse_args();assert not a.out.exists()
 sys.path[:0]=[str(a.source/'tools'),str(a.source/'tools/s81_dv'),str(a.source/'tools/s81_dv/layer_prog')]
 import numpy as np
 import hdc_golden_v41 as G
 import v41_rom_ksplit_bankmap as S
 import frame_return_plan as FP
 assert FP.OPTAG==1, "retained first-operation tag authority changed"
 files=json.loads((a.fixture/'files.json').read_text());f=json.loads((a.field/'field.json').read_text());ph=f['phases'][0]
 assert ph['mat']=='wq_a' and len(ph['row_index'])==4
 def arr(name):
  m=files[name];return np.fromfile(a.fixture/name,dtype=np.dtype(m['dtype'])).reshape(m['shape'])
 x=arr('ops/attn.norm.scale.bin').reshape(-1);xq,xe=G.quant_fp8(x)
 rows=ph['row_index'];codes=arr('weights/wq_a.bin')[rows];exp=arr('weights/wq_a.scale.bin')[np.asarray(rows)//32].astype(np.int64)-127
 w=G.E4M3[codes];blocks=np.stack([np.ldexp((w[:,32*b:32*(b+1)]@xq[32*b:32*(b+1)]).astype(G.F),exp[:,b]+xe[b]).astype(G.F)for b in range(len(x)//32)],axis=-1)
 segs=S.segments(len(x),ph['nseg']);gold={str(row):[int(G.bits(G.csum(blocks[i,lo//32:(lo+n)//32])))for lo,n in segs]for i,row in enumerate(rows)}
 cfg=[]
 for bank in range(7):cfg.append([int(v,16)for v in(a.field/'images'/f'u_f_0L01_c0_{bank}.viamap.hex').read_text().split()])
 def word(bank,address):return sum(((cfg[bank][address//8]>>(8*b+address%8))&1)<<b for b in range(72))
 words=[word(k%7,k//7)for k in range(25)];expected=[]
 for slot in range(8):
  if not words[8+slot]&1:continue
  seg=(words[slot]>>16)&31;n=(words[slot]>>21)&31
  for mb,k in [(0,slot),(1,17+slot)]:
   raw=words[k]&65535
   if raw&0x8000:continue
   row=raw&16383;assert row in rows and n==ph['nseg'] and seg<n
   expected.append(dict(macro=mb,row=row,segment=seg,nseg=n,pos=0,value=gold[str(row)][seg]))
 assert expected
 names=['ops/attn.norm.scale.bin','weights/wq_a.bin','weights/wq_a.scale.bin']
 report=dict(rows=rows,nseg=ph['nseg'],status='PREPARED_CHECKPOINT_GOLD_GB_SPLIT_QUAL',frame=f['frame'],phase=0,selected_native_leaf='u_f_0L01.u_r0.u_e0',expected_each_operation=expected,gold_rows=gold,first_operation_tag=int(FP.OPTAG),frame_model_sha256=hashlib.sha256(Path(FP.__file__).read_bytes()).hexdigest(),operation_tag_rule='native consumed count after each broadcast, modulo4; OPTAG1 original first operation',source_sha256={name:hashlib.sha256((a.fixture/name).read_bytes()).hexdigest()for name in names},production_enabled=False)
 a.out.write_text(json.dumps(report,indent=2)+'\n');print('PREPARED_NATIVE_SPLIT_GOLD',expected,flush=True)
if __name__=='__main__':main()
