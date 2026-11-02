#!/usr/bin/env python3
"""Bounded genuine row slices and REFERENCE-only L6 prefix inputs for S8 post.

Never regenerate weights, copy the full image, or label L6 reference streams as
executed ME results. Collector port ordering remains a separate source join.
"""
import argparse,hashlib,json,sys
from pathlib import Path

CODE_SHA='5f254e2074491e2927a7ed36c3b17ff8bf66add69b1f2f5caa61049f12080b80'
CAPTURE_SHA='c3db0ddac19d2e7d4803ca2300eb3409d16aef47279c44fbf2660b7899e815b3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract(source,out):
 h=hashlib.sha256();records=[];n=0
 with source.open('rb')as f:
  for index,line in enumerate(f):
   h.update(line);n+=1
   if index<64:
    text=line.strip();assert len(text)==98304
    records.append(dict(block=0,word=index,group_first=0,groups=512,hex=text[-16384:].decode()))
   elif 1536<=index<1600 and(index-1536)%8<3:
    text=line.strip();assert len(text)==98304
    records.append(dict(block=148,word=index,group_first=2048,groups=512,hex=text[-81920:-65536].decode()))
 assert n==1600 and len(records)==88 and h.hexdigest()==CODE_SHA
 out.write_text(json.dumps(dict(scope='EXISTING_GENUINE_ROW_BLOCK_SLICES_REFERENCE_INPUT_ONLY',source=str(source),source_sha256=h.hexdigest(),blocks=[0,148],code_bytes=720896,records=records))+'\n')

def reference(a):
 sys.path.insert(0,str(a.tools));import hdc_golden as G
 import numpy as np
 a.out.mkdir(parents=True,exist_ok=True)
 subject=json.loads(a.slices.read_text());assert subject['source_sha256']==CODE_SHA and len(subject['records'])==88 and subject['code_bytes']==720896
 stage=json.loads(a.head.read_text());gains=np.zeros(4096,dtype=np.uint32);seen=set()
 for sl in stage['slices']:
  sid=sl['slice']
  for rec in sl['crom']:
   assert 68<=rec['addr']<92
   word=int(rec['payload_hex'],16)
   for lane in range(16):
    local=16*(rec['addr']-68)+lane;global_i=(local//128*12+sid)*128+local%128
    assert global_i<4096 and global_i not in seen and ((word>>(64*lane+32))&0xffffffff)==0
    seen.add(global_i);gains[global_i]=(word>>(64*lane))&0xffffffff
 assert len(seen)==4096
 rstd=G.rsqrt(np.float32(1024));assert int(G.bits(rstd))==0x3cffffff
 rawh=G.mul(G.mul(np.float32(32),rstd),G.from_bits(gains));h=G.to_bf16(rawh)
 expected32=[int(x,16)for x in a.h32.read_text().split()];assert list(map(int,G.bits(h[:32])))==expected32
 (a.out/'H4096_me_fp32_REFERENCE.hex').write_text(''.join(f'{int(x):08x}\n'for x in G.bits(h)))
 capture=[]
 assert sha(a.capture)==CAPTURE_SHA
 for line in a.capture.read_text().splitlines():
  if line.startswith('#'):continue
  ix,time,value=line.split();assert int(ix)==len(capture);capture.append(int(value,16))
 assert len(capture)==1600
 scales=[int(x,16)for x in a.scales.read_text().split()];assert len(scales)==1200
 report=[];l6_lines=['# REFERENCE_ONLY block logical_stream k slot lanes15_to0_fp32_hex'];raw_lines=['# REFERENCE_ONLY block slot full512split_raw_lanes15_to0_hex'];scaled_lines=['# REFERENCE_ONLY block slot full512split_scaled_lanes15_to0_hex'];actualcheck=[]
 def packed(bits):return ''.join(f'{int(x):08x}'for x in bits[::-1])
 def tree(x):
  while x.shape[1]>1:x=G.add(x[:,0::2],x[:,1::2])
  return x[:,0]
 for block,slots,base,scale0 in [(0,8,0,0),(148,3,1536,1184)]:
  w=np.zeros((16*slots,512,8),dtype=np.float32);records=[x for x in subject['records']if x['block']==block]
  assert len(records)==8*slots
  for rec in records:
   k,slot=divmod(rec['word']-base,8);assert 0<=k<8 and slot<slots
   codes=np.frombuffer(bytes.fromhex(rec['hex'])[::-1],dtype=np.int8).reshape(512,16)
   w[16*slot:16*(slot+1),:,k]=codes.T
  acc=np.zeros((16*slots,512),dtype=np.float32);full=None
  for k in range(8):
   acc=G.add(acc,G.mul(w[:,:,k],h.reshape(512,8)[:,k][None,:]))
   l6=np.stack([tree(acc[:,64*i:64*(i+1)])for i in range(8)],axis=1)
   for stream in range(8):
    for slot in range(slots):l6_lines.append(f'{block} {stream} {k} {slot} '+packed(G.bits(l6[16*slot:16*(slot+1),stream])))
   full=tree(l6)
   if block==0:
    four=tree(acc[:,:4])
    for slot in range(8):
     ordinal=8*k+slot;bits=G.bits(four[16*slot:16*(slot+1)]);expect=int(packed(bits),16)
     assert expect==capture[ordinal],('ACTUAL_TG4_PREFIX_MISMATCH',ordinal)
     actualcheck.append(dict(raw_ordinal=ordinal,k=k,slot=slot,actual_and_reference_lanes15_to0=packed(bits)))
  direct=G.matvec(w.reshape(16*slots,4096),h,512);assert np.array_equal(G.bits(full),G.bits(direct))
  for slot in range(slots):
   raw_bits=G.bits(full[16*slot:16*(slot+1)]);raw_lines.append(f'{block} {slot} '+packed(raw_bits))
   scale=np.array([(scales[scale0+slot]>>(16*l))&65535 for l in range(16)],dtype=np.uint32)
   scaled=G.mul(G.from_bits(raw_bits),G.from_bits(scale<<16));assert np.all(np.isfinite(scaled));scaled_lines.append(f'{block} {slot} '+packed(G.bits(scaled)))
  report.append(dict(block=block,rows=[block*128,block*128+16*slots],row_count=16*slots,slots=slots,source_words=len(records),code_bytes=16*slots*4096,reference_L6_streams=8,per_stream_Kprefix_vectors=8*slots,expected_final_vectors=slots,scale_words=list(range(scale0,scale0+slots))))
 for name,lines in [('L6_prefix_streams_REFERENCE.tsv',l6_lines),('full512_raw_REFERENCE.tsv',raw_lines),('full512_scaled_REFERENCE.tsv',scaled_lines)]:
  (a.out/name).write_text('\n'.join(lines)+'\n')
 (a.out/'actual_TG4_block0_crosscheck.json').write_text(json.dumps(dict(scope='ACTUAL_PASS_NATIVE_TG4 raw0..63 vs independently computed first4logicalgroups; not L6 execution',capture_sha256=CAPTURE_SHA,matched_vectors=64,matched_FP32_values=1024,rows=actualcheck),indent=2)+'\n')
 outputs={p.name:sha(p)for p in a.out.iterdir()if p.is_file()and p.name!='reference_receipt.json'}
 receipt=dict(status='REFERENCE_POST_BOUNDARY_INPUTS_READY_NOT_EXECUTED_L6',blocks=report,code_bytes=720896,selected_code_words=88,total_rows=176,total_REFERENCE_L6_prefix_vectors=704,total_REFERENCE_L6_FP32_values=11264,canonical_RSTD='3cffffff',H='canonical32*rsqrt1024*actual4096normgains then BF16RNE expandedFP32',logical_stream_groups=[[64*i,64*(i+1)]for i in range(8)],arithmetic='eachgroup8sequentialRNEprefixes from+0; pairwise64group tree per logical L6 stream; final512tree then genuineBF16rowmul',actual_crosscheck=dict(vectors=64,values=1024,scope='TG4 first4logicalgroups block0 only',capture_sha256=CAPTURE_SHA),physical_port_mapping='UNRESOLVED: logical streams0..7 are reference group intervals, not guessed fs/ns/fn/nn legs or clock aliases',scope='NoexecutedL6/fullME/global512post/STN/AMAXclaim; referenceinputs+goldenonly; no costly EDA/simulation dispatch',readset={str(p):sha(p)for p in [a.slices,a.head,a.h32,a.scales,a.capture,a.tools/'hdc_golden.py',a.tools/'hdc_qwen_int8_image_w12.py']},outputs=outputs)
 (a.out/'reference_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],receipt['actual_crosscheck'])

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 e=sub.add_parser('extract');e.add_argument('--source',type=Path,required=True);e.add_argument('--out',type=Path,required=True)
 r=sub.add_parser('reference')
 for k in ('tools','slices','head','h32','scales','capture','out'):r.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args()
 if a.command=='extract':extract(a.source,a.out)
 else:reference(a)
if __name__=='__main__':main()
