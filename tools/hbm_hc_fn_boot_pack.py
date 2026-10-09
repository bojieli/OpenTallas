#!/usr/bin/env python3
"""Bit-preserving HC FN boot producer for the sharded F32 row operand SRAM.

A row has8 term banks,80 live words/bank,32 lanes/word,4 sectors/word.
Bank stride reserves128 words; loader writes only8 live contiguous regions.
No conversion to/from host float occurs. Manifest-only is NOT a boot image.
"""
import argparse,hashlib,json,re,struct
from pathlib import Path
import numpy as np
K=20480; ROW_BYTES=K*4; APERTURE_BYTES=131072

def sha(b):return hashlib.sha256(b).hexdigest()
def pack_row(raw):
 if len(raw)!=ROW_BYTES:raise ValueError('F32 row must contain81920 bytes')
 words=np.frombuffer(raw,dtype='<u4').reshape(80,32,8).transpose(2,0,1)
 out=np.zeros((8,128,32),dtype='<u4');out[:,:80,:]=words
 return out.tobytes()
def unpack_row(packed):
 if len(packed)!=APERTURE_BYTES:raise ValueError('row aperture must contain131072 bytes')
 return np.frombuffer(packed,dtype='<u4').reshape(8,128,32)[:,:80,:].transpose(1,2,0).copy().tobytes()
def catalogue(headers,nsub):
 records={}; pins={}
 for p in sorted(headers.glob('model-*.safetensors.header.json')):
  raw=p.read_bytes();h=json.loads(raw);pins[p.name]=sha(raw)
  for name,t in h.items():
   m=re.fullmatch(r'(layers|mtp)\.(\d+)\.hc_(attn|ffn)_fn',name)
   if not m:continue
   s=(80 if m[1]=='mtp' else 0)+2*int(m[2])+int(m[3]=='ffn')
   if t.get('dtype')!='F32' or t.get('shape')!=[24,K]:raise ValueError(name+' shape/dtype')
   if t['data_offsets'][1]-t['data_offsets'][0]!=24*ROW_BYTES:raise ValueError(name+' byte length')
   if s in records:raise ValueError('duplicate tensor')
   records[s]={'sublayer':s,'tensor':name,'shard':p.name.removesuffix('.header.json'),**t}
 if set(records)!=set(range(86)):raise ValueError('catalogue must contain all86released fn tensors')
 return [records[s] for s in range(nsub)],pins

def manifest(headers,nsub,base_sector):
 tensors,pins=catalogue(headers,nsub);tasks=[]
 if base_sector<0 or base_sector+(22*4096)>=1<<30:raise ValueError('sector aperture exceeds30-bit address')
 for t in tensors:
  for row in range(24):
   task=t['sublayer']*24+row;die=task%96;slot=task//96
   tasks.append({'tensor':t['tensor'],'sublayer':t['sublayer'],'row':row,'die':die,'slot':slot,
    'input_row_offsets':[t['data_offsets'][0]+row*ROW_BYTES,t['data_offsets'][0]+(row+1)*ROW_BYTES],
    'hbm_base_sector':base_sector+slot*4096})
 return {'schema':'opentallas.hbm.hc_fn_boot.v1','status':'HEADER_CONTRACT_PAYLOAD_PENDING',
  'sub_layers':nsub,'headers_sha256':pins,'tensors':tensors,'rows':tasks,
  'loader_contract':{'sector_bytes':32,'live_sector_count_per_row':2560,'reserved_sector_count_per_row':4096,
   'bank_count':8,'bank_stride_sectors':512,'live_sectors_per_bank':320,
   'address':'hbm_base_sector+bank*512+word*4+beat',
   'word':'fn[row][8*(word*32+lane)+bank] as original little-endian32bits',
   'command':'target die,30-bit sector address,data256,all32byte strobes; wait physical write fence before READY',
   'regions':'8 contiguous320sector writes per row; padding sectors not fetched',
   'storage':'HBM fn payload gets normal HBM reliability; on-die SRAM gets SECDED; no ROM ECC'}},tensors

def verify():
 rng=np.random.default_rng(20261009)
 raw=rng.integers(0,1<<32,K,dtype=np.uint32).astype('<u4').tobytes()
 packed=pack_row(raw);assert unpack_row(packed)==raw
 words=np.frombuffer(raw,dtype='<u4');p=np.frombuffer(packed,dtype='<u4').reshape(8,128,32)
 for bank in range(8):
  for word in range(80):
   for lane in range(32):assert p[bank,word,lane]==words[8*(word*32+lane)+bank]
 assert np.all(p[:,80:,:]==0)
 mutant=p.copy();mutant[[0,1]]=mutant[[1,0]]
 assert unpack_row(mutant.tobytes())!=raw
 # Payload includes allbit patterns,including NaN/Inf encodings,withoutcasts.
 return {'status':'PASS','words_exact':K,'negative_bank_swap':'REJECTED',
  'input_sha256':sha(raw),'packed_sha256':sha(packed)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--headers',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True);ap.add_argument('--checkpoint-dir',type=Path)
 ap.add_argument('--mtp',action='store_true');ap.add_argument('--base-sector',type=int,default=0)
 ap.add_argument('--verify',action='store_true');a=ap.parse_args()
 m,ts=manifest(a.headers,86 if a.mtp else 80,a.base_sector)
 if a.verify:m['swizzle_gate']=verify()
 if a.output.exists():raise FileExistsError('immutable output already exists')
 if a.checkpoint_dir:
  a.output.parent.mkdir(parents=True,exist_ok=True);images={};payload_pins={}
  for t in ts:
   path=a.checkpoint_dir/t['shard']
   with path.open('rb') as f:
    n=struct.unpack('<Q',f.read(8))[0];live_header=json.loads(f.read(n))
    if live_header[t['tensor']]!={k:t[k] for k in ('dtype','shape','data_offsets')}:raise ValueError('live header mismatch')
    f.seek(8+n+t['data_offsets'][0]);raw=f.read(24*ROW_BYTES)
   if len(raw)!=24*ROW_BYTES:raise ValueError('truncated checkpoint')
   payload_pins[t['tensor']]=sha(raw)
   for row in range(24):
    task=t['sublayer']*24+row;die=task%96;slot=task//96
    out=a.output.parent/f'fn_die{die:02d}.bin'
    packed=pack_row(raw[row*ROW_BYTES:(row+1)*ROW_BYTES])
    assert unpack_row(packed)==raw[row*ROW_BYTES:(row+1)*ROW_BYTES]
    if die not in images and out.exists():raise FileExistsError('immutable die image already exists')
    with out.open('r+b' if die in images else 'w+b') as f:f.seek(slot*APERTURE_BYTES);f.write(packed)
    images[die]=out
  m['status']='PAYLOAD_PACKED_INVERSE_EXACT_LOADER_INTEGRATION_PENDING'
  m['payload_sha256']=payload_pins;m['image_sha256']={p.name:sha(p.read_bytes()) for p in images.values()}
 m['producer_sha256']=sha(Path(__file__).read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
