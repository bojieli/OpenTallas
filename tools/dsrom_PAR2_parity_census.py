#!/usr/bin/env python3
"""Project frozen allocation metadata into finite local parity bank envelopes.
No payload, reallocation, encoding or issue schedule inference.
"""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
SOURCE_SHA='c91855b5b33c21c56dac3ea9ebc69a201ff582a3a6ad67a19024e89cd113881f'
def extract(path):
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=SOURCE_SHA:raise ValueError('not frozen622 metadata journal')
 phases=collections.Counter();out=[];worst=None;count=0
 for ordinal,line in enumerate(gzip.decompress(data).splitlines()):
  r=json.loads(line);s=r['stage'];phase=phases[s];phases[s]+=1;count+=1
  if r['format']!='fp4':continue
  groups=collections.defaultdict(list);prefix=0
  for si,pair,first,n,stride,start,w in r['plans']:
   if pair>=2048:groups[si].append([si,pair,r['ecc_bit_base']+prefix,n*w*16,n,w])
   prefix+=n*w*16
  for seg,runs in groups.items():
   eligible=collections.defaultdict(set);firstrows=collections.defaultdict(set);requests=collections.defaultdict(list)
   for si,pair,base,bits,n,w in runs:
    lo=base//256;hi=(base+bits-1)//256
    for chunk in range(lo//8192,hi//8192+1):
     for parity in (0,1):
      a=max(lo,chunk*8192);z=min(hi,(chunk+1)*8192-1)
      if a+((parity-a)%2)<=z:eligible[(chunk,parity)].add(pair)
    k=lo//8192,lo%2;firstrows[k].add((lo%8192)//2);requests[k].append([pair,base])
   peak=max(map(len,eligible.values()),default=0);sample=max(map(len,firstrows.values()),default=0)
   rec=dict(ordinal=ordinal,stage=s,phase=phase,segment=seg,active_pairs=len({x[1] for x in runs}),eligible_leaf_distinct_pair_upper=peak,first_address_batch_distinct_row_peak=sample)
   out.append(rec)
   if worst is None or sample>worst['distinct_rows']:
    k=max(firstrows,key=lambda k:len(firstrows[k]));worst=dict(distinct_rows=sample,source_record=rec,leaf_chunk_parity=list(k),requests_pair_linearbit=requests[k],schedule_scope='Adversarial address-service witness; simultaneous actual engine issue not established.')
 return dict(source_commit='622dbc897fd5ecb5a5b691e1ae39bea0ad751524',source_path='results/uarch/dsrom_owner_provider_first_20261002/r1/assignments.jsonl.gz',source_sha256=SOURCE_SHA,source_records=count,formula='ecc_bit_base + sum(previous_run.n*words*16) + (a-start)*16 + mb*8',records=out,worst_first_address_witness=worst,payload_reads=0,interval_projection='All shard1 FP4 source run intervals examined; eligible leaf union per segment; no allocator reexecution.',actual_issue_calendar=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('source_journal',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 data=gzip.compress((json.dumps(extract(a.source_journal),sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
 if a.output.exists() and a.output.read_bytes()!=data:raise ValueError('immutable projection changed')
 a.output.write_bytes(data);print(hashlib.sha256(data).hexdigest())
if __name__=='__main__':main()
