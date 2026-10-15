#!/usr/bin/env python3
"""Bounded exact inverse-map and byte verification of full-SM source images."""
import argparse,hashlib,json,struct
from pathlib import Path
from hbm_checkpoint_native_plan import ROOT,descriptor,block_bytes
from hbm_checkpoint_native_readback import inverse
from hbm_checkpoint_native_stream import digest
from w19_payload_loader import compact_sectors

def check(directory,mutant=None):
 directory=Path(directory);r=json.loads((directory/'receipt.json').read_text());rp=ROOT/'results/arch/hbm_die_v15/checkpoint_residency/receipt.json';res=json.loads(rp.read_text())
 if r['source_sha256'][str(rp.relative_to(ROOT))]!=digest(rp):raise ValueError('residency source mismatch')
 sectors=records=blocks=idle=0;last_matrix=-1;next_expert=0;binaryhash=hashlib.sha256();recordhash=hashlib.sha256()
 with (directory/'physical_pairs.bin').open('rb') as phy,(directory/'records.bin').open('rb') as logical,(directory/'operations.jsonl').open() as ops:
  for line in ops:
   o=json.loads(line);i=o['matrix'];m=res['matrices'][i]
   if i==last_matrix:
    if o.get('idle') or o['expert']!=next_expert:raise ValueError('missing/duplicate expert')
   else:
    if i!=last_matrix+1 or last_matrix>=0 and next_expert not in (0,res['matrices'][last_matrix]['experts']):raise ValueError('missing matrix/expert')
    next_expert=0;last_matrix=i
   rows,stride=block_bytes(m,r['rank'],r['sm'])
   if o.get('idle'):
    if rows or o['experts']!=m['experts']:raise ValueError('invented idle matrix')
    idle+=1;continue
   if not rows:raise ValueError('invented active rows')
   d=descriptor(res,r['rank'],r['sm'],i,next_expert)
   if d!=o['descriptor'] or sectors!=d['packed_sector_offset']:raise ValueError('operation descriptor mismatch')
   op_hash=hashlib.sha256()
   def lines():
    nonlocal records
    for _ in range(d['payload_records']):
     b=logical.read(136)
     if len(b)!=136:raise ValueError('missing actual source record')
     op_hash.update(b);recordhash.update(b);records+=1;yield b
   for expected in compact_sectors(lines(),d['payload_records']):
    pair=phy.read(36)
    if len(pair)!=36:raise ValueError('missing physical pair')
    binaryhash.update(pair);s=struct.unpack('<I',pair[:4])[0];data=pair[4:]
    if mutant=='address' and sectors==0:s=0
    if mutant=='payload' and sectors==0:data=bytes([data[0]^1])+data[1:]
    if inverse(s,d)!=sectors:raise ValueError('wrong physical address')
    if data!=expected:raise ValueError('payload mismatch')
    sectors+=1
   if op_hash.hexdigest()!=o['source_payload_sha256']:raise ValueError('source operation hash')
   next_expert+=1;blocks+=1
  if last_matrix!=len(res['matrices'])-1 or next_expert not in (0,res['matrices'][last_matrix]['experts']):raise ValueError('incomplete source matrix domain')
  if phy.read(1) or logical.read(1):raise ValueError('extra physical/source bytes')
 if sectors!=r['sectors'] or records!=r['records'] or blocks!=r['active_matrix_expert_blocks'] or idle!=r['idle_matrices']:raise ValueError('full image count')
 if binaryhash.hexdigest()!=r['physical_pairs_binary_sha256'] or recordhash.hexdigest()!=r['logical_records_binary_sha256']:raise ValueError('full image hash')
 return dict(rank=r['rank'],sm=r['sm'],sectors=sectors,records=records,active_expert_blocks=blocks,idle_matrices=idle,all545_matrix_assignments_checked=True,actual_HBM_ACK=False,actual_HBM_readback=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--mutants',action='store_true');a=p.parse_args();positive=check(a.directory)
 if a.mutants:
  for m in ['address','payload']:
   try:check(a.directory,m)
   except ValueError:positive[m+'_mutant_rejected']=True
   else:raise AssertionError('mutant survived')
 out=Path(a.directory)/'software_verification.json';out.write_text(json.dumps(positive,indent=2)+'\n');print(json.dumps(positive))
