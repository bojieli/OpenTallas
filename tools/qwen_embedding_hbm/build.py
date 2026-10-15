#!/usr/bin/env python3
"""Build the complete released embedding HBM image using the shipped W8 quantizer."""
from pathlib import Path
import argparse,hashlib,json,sys,zlib,platform
import numpy as np
import torch
from safetensors import safe_open
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from qwen3_deployment_quality import quantize_w8
V,H=151936,4096


def sha(path):
 digest=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for part in iter(lambda:stream.read(8<<20),b''):digest.update(part)
 return digest.hexdigest()


def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--threads',type=int,default=16);p.add_argument('--vectors',type=Path)
 p.add_argument('--finish-existing-quantization',action='store_true',help='Finalize complete payloads with preserved quantization_source.py and quantization.log')
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=a.finish_existing_quantization);torch.set_num_threads(a.threads)
 if (a.out/'manifest.json').exists():raise ValueError('refusing to overwrite completed image')
 lock_path=ROOT/'compiler/models/qwen3-8b/checkpoint_source.json';lock=json.loads(lock_path.read_text())
 if a.snapshot.name!=lock['revision']:raise ValueError('wrong actual checkpoint revision')
 entries={x['path']:x for x in lock['expected_files']}
 index=a.snapshot/lock['checkpoint_index']
 if sha(index)!=entries[index.name]['sha256']:raise ValueError('checkpoint index pin mismatch')
 mapping=json.loads(index.read_text())['weight_map'];key='model.embed_tokens.weight';shard=a.snapshot/mapping[key]
 if shard.stat().st_size!=entries[shard.name]['size_bytes'] or sha(shard)!=entries[shard.name]['sha256']:raise ValueError('actual embedding source shard pin mismatch')
 if a.finish_existing_quantization:
  log=a.out/'quantization.log';generator=a.out/'quantization_source.py'
  if sha(generator)!='3412dd0321b65b87cdc295626f641a6c8fa9c5e00fb587b37381160bde096274':raise ValueError('unrecognized preserved quantizer invocation source')
  seen=[tuple(map(int,line.split()[1:])) for line in log.read_text().splitlines() if line.startswith('EMBEDDING_QUANTIZED ')]
  if seen!=[(first,min(first+4096,V)) for first in range(0,V,4096)]:raise ValueError('incomplete/duplicate quantization progress evidence')
  if (a.out/'embedding_codes.bin').stat().st_size!=V*H or (a.out/'embedding_scales_bf16.bin').stat().st_size!=V*2:raise ValueError('incomplete quantized payload')
  codes=np.memmap(a.out/'embedding_codes.bin',mode='r',dtype=np.int8,shape=(V,H))
  scales=np.memmap(a.out/'embedding_scales_bf16.bin',mode='r',dtype='<u2',shape=(V,))
 else:
  codes=np.memmap(a.out/'embedding_codes.bin',mode='w+',dtype=np.int8,shape=(V,H))
  scales=np.memmap(a.out/'embedding_scales_bf16.bin',mode='w+',dtype='<u2',shape=(V,))
  with safe_open(str(shard),framework='pt',device='cpu') as sf:
   tensor=sf.get_slice(key)
   if tuple(tensor.get_shape())!=(V,H):raise ValueError('wrong full embedding shape')
   for first in range(0,V,4096):
    last=min(first+4096,V);w=tensor[first:last]
    if w.dtype!=torch.bfloat16:raise ValueError('wrong released embedding dtype')
    q,s,_=quantize_w8(w.to(torch.float32))
    codes[first:last]=q.numpy();scales[first:last]=s.view(torch.int16).numpy().view(np.uint16).reshape(-1)
    codes.flush();scales.flush();print('EMBEDDING_QUANTIZED',first,last,flush=True)
 sources=[]
 if a.vectors:
  for token in [0,65536,151935]:
   directory=a.vectors/f'token{token}'
   words=[int(x,16) for x in (directory/'codes.hex').read_text().splitlines()]
   got=[int.from_bytes(codes[token,64*k:64*(k+1)].view(np.uint8).tobytes(),'little') for k in range(64)]
   scale=int((directory/'scale.hex').read_text().strip(),16)
   if got!=words or int(scales[token])!=scale:raise ValueError(f'released historical embedding token vector mismatch:{token}')
   sources.append(dict(token=token,codes_sha256=sha(directory/'codes.hex'),scale_sha256=sha(directory/'scale.hex')))
 # Logical E identifies each 32-byte code/scale sector. Keep compact payloads;
 # the exact deployed 281-bit boot-hex representation is available through emit_boot.py.
 count=V*128+V//16;checksum=0;pcs=[0]*128
 for first in range(0,V,4096):
  raw=codes[first:min(first+4096,V)].view(np.uint8).reshape(-1,32)
  for local,row in enumerate(raw):
   e=first*128+local;checksum+=zlib.crc32(e.to_bytes(4,'little')+row.tobytes())
   pcs[e&127]+=1
  print('HBM_CODE_CHECKSUM',first,flush=True)
 for g in range(V//16):
  e=V*128+g;checksum+=zlib.crc32(e.to_bytes(4,'little')+scales[16*g:16*g+16].tobytes());pcs[g&127]+=1
 checksum&=0xffffffff
 files=[Path(__file__),ROOT/'tools/qwen_embedding_hbm/emit_boot.py',ROOT/'tools/qwen3_deployment_quality.py',ROOT/'tools/emb_hbm_bench.py',lock_path]
 record=dict(schema='opentallas.qwen-released-embedding-hbm.v1',checkpoint_revision=lock['revision'],checkpoint_lock_sha256=sha(lock_path),
  source_tensor=key,source_shape=[V,H],source_dtype='BF16',source_shard=str(shard),source_shard_sha256=sha(shard),index_sha256=sha(index),
  quantization='unchanged deployed quantize_w8: full output row INT8 MSE search21 with BF16 row scale',
  sources={str(path.relative_to(ROOT)):sha(path) for path in files},historical_token_vectors=sources,
  recovered_quantization=dict(source_sha256=sha(a.out/'quantization_source.py'),log_sha256=sha(a.out/'quantization.log')) if a.finish_existing_quantization else None,
  runtime=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__),
  embedding_codes=dict(file='embedding_codes.bin',dtype='int8',shape=[V,H],sha256=sha(a.out/'embedding_codes.bin')),
  embedding_scales=dict(file='embedding_scales_bf16.bin',dtype='little-endian BF16 bits uint16',shape=[V],sha256=sha(a.out/'embedding_scales_bf16.bin')),
  hbm=dict(sector_bits=256,code_sectors=V*128,scale_base=V*128,scale_sectors=V//16,end=count,
   sectors=count,payload_bytes=V*H+V*2,boot_checksum=checksum,per_stack_pc_sector_counts=pcs,
   boot281='(little_endian_payload256 << 25) | E25',hb283='(payload256 << 27) | (E25 << 2) | 1',
   marker_hb283='((checksum32 << 32 | sector_count32) << 27) | 3',
   checksum='sum(zlib.crc32(E.to_bytes(4,little)+payload32)) modulo 2**32',
   code_address='token=E>>7;i=E&127;stack=i>>5;pc=i&31;p=token&1023;row=token>>10;bank=((p>>7)<<2)|(p&3);column=(p>>2)&31',
   scale_address='s=E-scale_base;stack=(s>>5)&3;pc=s&31;p=384+(s>>7);row=148;bank=((p>>7)<<2)|(p&3);column=(p>>2)&31'),
  native_embedding_qualified=False,remaining=['actual selected gateway/controller/static runtime consumer RTL proof'])
 (a.out/'manifest.json').write_text(json.dumps(record,indent=1)+'\n')
 print('PASS_COMPLETE_RELEASED_EMBEDDING_HBM tokens151936 dims4096 sectors'+str(count)+' checksum'+str(checksum),flush=True)
if __name__=='__main__':main()
