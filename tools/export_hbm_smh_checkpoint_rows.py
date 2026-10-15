#!/usr/bin/env python3
"""Export actual released DS L0wq_a rank share into original136-byte SM lines.

This selects the immutable W19 TP96 row partition and the original32-SM
ceil-share partition. No allocator address is invented. Output is a payload,
not hardware installation or native numerical qualification.
"""
import argparse,hashlib,json,struct,sys
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def export(snapshot,out,rank):
 snapshot=Path(snapshot);out=Path(out)
 if not 0<=rank<96:raise ValueError('actualTP96rankrequired')
 index_path=snapshot/'model.safetensors.index.json';index_raw=index_path.read_bytes();index=json.loads(index_raw)
 name='layers.0.attn.wq_a.weight';scale='layers.0.attn.wq_a.scale'
 shard=snapshot/index['weight_map'][name]
 if index['weight_map'][scale]!=shard.name:raise ValueError('weight/scale share source shard expected')
 with shard.open('rb') as f:
  nh=struct.unpack('<Q',f.read(8))[0];header_raw=f.read(nh);h=json.loads(header_raw);base=8+nh
  wm,sm=h[name],h[scale]
  if wm['dtype']!='F8_E4M3' or wm['shape']!=[1280,5120] or sm['dtype']!='F8_E8M0' or sm['shape']!=[40,160]:raise ValueError('releasedproductiontensor shape/type mismatch')
  r0=rank*1280//96;r1=(rank+1)*1280//96
  f.seek(base+wm['data_offsets'][0]+r0*5120);weights=f.read((r1-r0)*5120)
  sr0=r0//32;sr1=(r1+31)//32
  f.seek(base+sm['data_offsets'][0]+sr0*160);scales=f.read((sr1-sr0)*160)
 # Independentexistingcheckpoint packer and originalissue-order reference.
 from hgi_e2e import sm_lines as SL
 import hdc_golden_v41 as V
 import rtl_gpu_sm_exact as S
 wc=np.frombuffer(weights,dtype=np.uint8).reshape(r1-r0,5120)
 sc=np.frombuffer(scales,dtype=np.uint8).reshape(sr1-sr0,160)
 ex=np.stack([sc[(r0+r)//32-sr0].astype(np.int64)-127 for r in range(r1-r0)])
 ref=SL.pack(1,V.Q8(V.E4M3[wc].astype(np.float64),ex)).reshape(r1-r0,5,8,136)
 out.mkdir(parents=True,exist_ok=False)
 q=(r1-r0+31)//32;entries=[]
 for s in range(32):
  first=s*q;last=min((s+1)*q,r1-r0)
  if first>=last:entries.append(dict(sm=s,active=False,rows=0));continue
  lines=[]
  # Original issue GS order: item=row*G+group, each8-item wave traverses t,slot.
  items=[(row,g) for row in range(first,last) for g in range(5)]
  for wave in range(0,len(items),8):
   for t in range(8):
    for row,g in items[wave:wave+8]:
     line=bytearray(136)
     for j in range(4):
      block=(g*4+j)*8+t
      if block<160:
       off=row*5120+block*32;line[j*32:j*32+32]=weights[off:off+32]
       line[128+j]=scales[((r0+row)//32-sr0)*160+block]
     lines.append(bytes(line))
  expected=[bytes(ref[first+row,g,t]) for row,g,t in S.issue_order(last-first,5,8,True)]
  if lines!=expected:raise AssertionError('actualcheckpointpacker/originalissueorder mismatch')
  file=out/f'sm{s:02d}.lines.hex';raw=''.join(f'{int.from_bytes(v,"little"):0272x}\n' for v in lines).encode();file.write_bytes(raw)
  entries.append(dict(sm=s,active=True,global_rows=[r0+first,r0+last],rows=last-first,K=5120,fmt=1,c=8,groups=5,gs=True,lines=len(lines),file=file.name,sha256=sha(raw)))
 pins={p:sha((ROOT/p).read_bytes()) for p in ['tools/export_hbm_smh_checkpoint_rows.py','tools/hgi_e2e/sm_lines.py','tools/rtl_gpu_sm_exact.py','tools/hdc_golden_v41.py','tools/w19_hbm_tp96_isa.py','rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv']}
 manifest=dict(schema='opentallas.actual-checkpoint-sm-payload.v1',checkpoint_snapshot=str(snapshot),checkpoint_index_sha256=sha(index_raw),checkpoint_shard=str(shard.resolve()),checkpoint_shard_header_sha256=sha(header_raw),tensor=name,scale_tensor=scale,tensor_meta=wm,scale_meta=sm,selected_weight_bytes_sha256=sha(weights),selected_scale_bytes_sha256=sha(scales),rank=rank,tp=96,global_rows=[r0,r1],SMs=32,selection='W19 even(n) TP96 then actualsmrecord Q=ceil(localM/32); idleSMs explicit',issue_order='GS wave8(row*G+g),t0..7,slot0..7; onlyrealitems emit136B',source_sha256=pins,ops=entries,independent_verification='existingSL.pack exactE4M3/UE8M0 + originalS.issue_order bitexact all520records',qualified=False,remaining=['actual allocatorreservation and fullPCimage binding','real loader/WB/34band delivery','native83programme/resource/xwrite/numerical gate','physical timing and immutable price'])
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--out',required=True);p.add_argument('--rank',type=int,required=True);a=p.parse_args();r=export(a.snapshot,a.out,a.rank);print(json.dumps({k:r[k] for k in ['rank','global_rows','SMs','selected_weight_bytes_sha256','selected_scale_bytes_sha256']}))
