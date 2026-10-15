#!/usr/bin/env python3
"""Bounded full-SM released checkpoint stream, all matrix/expert slots explicit.

Binary address/data pairs use4byte sector30 +32byte payload, little endian.
An operation JSONL indexes exact ranges; no whole image is resident in memory.
Actual hardware command ACK/epoch/readback and programmes are separate gates.
"""
import argparse,hashlib,itertools,json,math,shutil,struct
from pathlib import Path
from dsrom_checkpoint import Checkpoint,DEFAULT_CHECKPOINT
from hbm_checkpoint_native_stream import Source,records,physical,digest
from hbm_checkpoint_native_plan import ROOT,descriptor,block_bytes

def export(snapshot,out,rank,sm):
 rp=ROOT/'results/arch/hbm_die_v15/checkpoint_residency/receipt.json';bp=ROOT/'results/arch/hbm_die_v15/full_native_checkpoint_plan/book.json'
 r=json.loads(rp.read_text());book=json.loads(bp.read_text());expected=r['rank_sm_reserved_bytes'][rank][sm]
 if book['source_sha256'][str(rp.relative_to(ROOT))]!=digest(rp):raise ValueError('source plan hash')
 ck=Checkpoint(snapshot)
 if digest(ck.root/'model.safetensors.index.json')!=r['checkpoint_index_sha256']:raise ValueError('checkpoint index')
 # Check ALL actual source shards exist before producing a partial long stream.
 missing=sorted({f for f in ck.index.values() if not (ck.root/f).is_file()})
 if missing:raise ValueError('missing actual checkpoint shards: '+str(missing))
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 if shutil.disk_usage(out).free<3*expected+(1<<30):out.rmdir();raise ValueError('headroom for bounded full-SM stream')
 imagehash=hashlib.sha256();logicalhash=hashlib.sha256();sector_count=0;record_count=0;active=0;idle=0;headers={};maxbuf=0
 with (out/'physical_pairs.bin').open('xb') as phy,(out/'records.bin').open('xb') as logical,(out/'operations.jsonl').open('x') as ops:
  for index,m in enumerate(r['matrices']):
   rows,stride=block_bytes(m,rank,sm)
   if not rows:
    ops.write(json.dumps(dict(matrix=index,key=m['key'],experts=m['experts'],idle=True,source_rows=0,sectors=0))+'\n');idle+=1;continue
   for expert in range(m['experts']):
    d=descriptor(r,rank,sm,index,expert)
    if d['packed_sector_offset']!=sector_count:raise ValueError('contiguous full-native image mismatch')
    source=Source(ck,m,expert,rank);buf=bytearray();oprecords=0;opsectors=0;opsha=hashlib.sha256()
    def emit(data):
     nonlocal sector_count,opsectors
     s=physical(sector_count,d);pair=struct.pack('<I',s)+data;phy.write(pair);imagehash.update(pair);sector_count+=1;opsectors+=1
    first_record=record_count
    for line in records(source,d):
     logical.write(line);logicalhash.update(line);opsha.update(line);record_count+=1;oprecords+=1;buf.extend(line)
     while len(buf)>=32:emit(bytes(buf[:32]));del buf[:32]
    while opsectors<d['sectors']:emit(bytes(buf)+bytes(32-len(buf)));buf.clear()
    if oprecords!=d['payload_records'] or opsectors!=d['sectors']:raise ValueError('actual source count')
    headers.update(source.sources);maxbuf=max(maxbuf,8*(source.max_row_bytes+m['packed_bytes_per_row']))
    ops.write(json.dumps(dict(matrix=index,expert=expert,descriptor=d,record_file_byte_offset=first_record*136,record_bytes=oprecords*136,physical_file_byte_offset=d['packed_sector_offset']*36,physical_file_bytes=opsectors*36,source_payload_sha256=opsha.hexdigest()))+'\n');active+=1
 if sector_count*32!=expected:raise AssertionError('full image exact reservation-used length')
 result=dict(schema='opentallas.hbm.full-SM-streamed-checkpoint.v1',status='ALL_SOURCE_MATRIX_EXPERT_ASSIGNMENTS_EXPORTED_INSTALL_REQUIRED',rank=rank,sm=sm,stack=sm//8,pcs=list(range(4*(sm%8),4*(sm%8)+4)),region_row_base=16640,region_row_count=2048,matrix_count=len(r['matrices']),active_matrix_expert_blocks=active,idle_matrices=idle,sectors=sector_count,records=record_count,padded_HBM_bytes=sector_count*32,physical_pairs_binary_sha256=imagehash.hexdigest(),logical_records_binary_sha256=logicalhash.hexdigest(),operation_manifest_sha256=digest(out/'operations.jsonl'),actual_checkpoint_bytes_read=ck.read_bytes,selected_tensor_header_count=len(headers),selected_tensor_header_sha256=hashlib.sha256(json.dumps(headers,sort_keys=True).encode()).hexdigest(),source_buffer_payload_bound_bytes=maxbuf,checkpoint_revision=r['checkpoint_revision'],checkpoint_index_sha256=r['checkpoint_index_sha256'],source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [rp,bp,Path(__file__).resolve(),ROOT/'tools/hbm_checkpoint_native_stream.py',ROOT/'tools/dsrom_checkpoint.py',ROOT/'tools/hbm_checkpoint_native_plan.py']},actual_HBM_ACK_verified=False,actual_HBM_readback_verified=False,native_programme_qualified=False,performance_qualified=False,physical_qualified=False)
 ck.close();(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['rank','sm','active_matrix_expert_blocks','idle_matrices','records','padded_HBM_bytes','actual_checkpoint_bytes_read']}));return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--enable-full-native',action='store_true');p.add_argument('--snapshot',default=str(DEFAULT_CHECKPOINT));p.add_argument('--out',required=True);p.add_argument('--rank',required=True,type=int,choices=range(96));p.add_argument('--sm',required=True,type=int,choices=range(32));a=p.parse_args()
 if not a.enable_full_native:p.error('explicit full-native mode required')
 export(a.snapshot,a.out,a.rank,a.sm)
