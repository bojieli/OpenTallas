#!/usr/bin/env python3
"""Apply source-proved TX198 map, retaining the full pre-round s2_x capture."""
import argparse,copy,gzip,hashlib,json,re
from pathlib import Path


def packed_bit(i):
 if i<128:return 16*(i//32)+(i%32)-16 if i%32>=16 else None
 if i<384:
  j=i-128;return 64+16*(j//32)+j%32-16 if j%32>=16 else None
 return i-192 if i<390 else None

def remap(endpoint):
 n,p=endpoint;m=re.fullmatch(r'(tx\d+_r[01])_(lo|hi)',n)
 if not m:return endpoint
 role,bit=re.fullmatch(r'([dq])\[(\d+)\]',p).groups();bit=int(bit)
 if n=='tx1_r0_hi'and bit>=128:return ['s2_x_full',f'{role}[{bit-128}]']
 logical=bit+(263 if m[2]=='hi'else 0);new=packed_bit(logical)
 return None if new is None else[m[1]+'_lo',f'{role}[{new}]']

def main():
 p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('pairs',type=Path);p.add_argument('source_inventory',type=Path);p.add_argument('out',type=Path);a=p.parse_args();c=json.loads(a.candidate.read_text());pairs=json.loads(gzip.decompress(a.pairs.read_bytes())if a.pairs.suffix=='.gz'else a.pairs.read_text());proof=json.loads(a.source_inventory.read_text());banks=[];old={b['inst']:b for b in c['banks']};removed=[]
 for b in c['banks']:
  m=re.fullmatch(r'(tx\d+_r[01])_(lo|hi)',b['inst'])
  if not m:banks.append(copy.deepcopy(b));continue
  if m[2]=='hi':removed.append(b['inst']);continue
  q=copy.deepcopy(b);q.update(inst=m[1]+'_lo',master='qkh_packet_v256',w=15.12,h=64.8,meaningful_payload_bits=198,source_bitmap=proof['layout']);banks.append(q)
 b=copy.deepcopy(old['tx1_r0_hi']);b.update(inst='s2_x_full',master='qkh_packet_v256',w=15.12,h=64.8,meaningful_payload_bits=128,purpose='full existing s2_x128 pre-RNE capture; no lost edge');banks.append(b)
 assert len(banks)==proof['data_banks']==58
 converted=[];dropped=[]
 for r in pairs:
  src=remap(r['source']);sink=remap(r['sink'])
  if src is None or sink is None:dropped.append(dict(group=r['group'],bit=r['bit'],reason='Source-proved unused TX X/W low16 capture bit; actual unchanged LSL ignores this field'));continue
  converted.append(dict(group=r['group'],bit=r['bit'],source=src,sink=sink))
 out=dict(schema='opentallas.qwen.tx198-geometry-inventory.v1',status='SOURCE_BITMAP_APPLIED_REQUIRES_GEOMETRY_TIMING',source_TX_inventory=proof,source_TX_inventory_sha256=hashlib.sha256(a.source_inventory.read_bytes()).hexdigest(),reference_candidate_sha256=hashlib.sha256(a.candidate.read_bytes()).hexdigest(),outline_um=c['outline_um'],children=c['children'],data_banks=banks,reset_nodes=c['reset_nodes'],expected_physical_bodies=83,residual_core=dict(home=None,source_state_census_required=True),fixed_capture_map=proof['alias_map'],cycle_ledger=dict(reference_staged_ledger='Preserve prior nodeinput/output/RQR/Xdelay compiler additions; TX198 adds0edges',TX198_extra_edges=0),parent_pin_ABI_changes='Existing face-bank translations remain candidate; no inherited finalpinroute qualification',qualification=False)
 assert len(out['children'])+len(banks)+len(out['reset_nodes'])==83
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'inventory.json').write_text(json.dumps(out,indent=2)+'\n');(a.out/'semantic_payload_pairs.json.gz').write_bytes(gzip.compress(json.dumps(converted,separators=(',',':')).encode(),mtime=0));(a.out/'pruned_source_bits.json.gz').write_bytes(gzip.compress(json.dumps(dropped,separators=(',',':')).encode(),mtime=0));print(json.dumps(dict(banks=len(banks),physical_bodies=83,payload_pairs=len(converted),source_proved_pruned_pairs=len(dropped),independent_s2_x_bits=128)))
if __name__=='__main__':main()
