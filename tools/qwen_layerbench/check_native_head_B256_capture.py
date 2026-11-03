#!/usr/bin/env python3
"""Validate complete actual consumed-ROM/raw-PART1 capture after baseline runs."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('packet',type=Path);a=p.parse_args()
receipt=json.loads((a.packet/'context_receipt.json').read_text());allrows=[];counts={'ROM':0,'RAW':0}; useful=0
for c in receipt['contexts']:
 d=a.packet/'contexts'/f"tile{c['tile']}";lines=(d/'actual_ROM_RAW_transcript_baseline.tsv').read_text().splitlines();seen={'ROM':0,'RAW':0};cycles={'ROM':[],'RAW':[]}
 gold={'ROM':(d/'rom_response_expected.hex').read_text().splitlines(),'RAW':(d/'raw_prefix_expected.hex').read_text().splitlines()}
 for line in lines:
  f=line.split('\t');kind=f[0];assert kind in seen and int(f[1])==c['tile'];i=int(f[2]);assert i==seen[kind] and i<64
  if kind=='ROM':assert len(f)==7 and int(f[3])==c['code_base']+i and int(f[5])-int(f[4])==9;cycle=int(f[5])
  else:assert len(f)==5;cycle=int(f[3])
  assert f[-1].lower()==gold[kind][i].lower();cycles[kind].append(cycle);seen[kind]+=1;counts[kind]+=1;allrows.append(line)
 assert seen=={'ROM':64,'RAW':64}
 for seq in cycles.values():assert all(b-a==1 for a,b in zip(seq,seq[1:])),('noncontinuous actual raw/request responses',c['tile'])
 useful+=c['reference_useful_vectors']
assert counts=={'ROM':16384,'RAW':16384} and useful==11264
out=a.packet/'actual_all_ROM_RAW.tsv';out.write_text('\n'.join(allrows)+'\n')
r=dict(status='PASS_ACTUAL_CAPTURE',counts=counts,required_subset_raw_vectors=useful,genuine_padding_raw_vectors=5120,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),scope='256 independent public ROM/PART1 contexts; raw TG4 only, no executed L6/full-logit claim',downstream_L6_contract=dict(contexts=16,raw_vectors_each=64,total_raw_vectors=1024,required_subset=704,padding=320,prefilter_allowed=False))
(a.packet/'actual_capture_receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
