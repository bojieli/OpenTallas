#!/usr/bin/env python3
"""Actual 53-source W0 payload producer map, preserving every slot and slice bit."""
import argparse,collections,gzip,json,pathlib,re

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();r=a.root;iv=json.load(open(r/'inventory.json'));ls=iv['leaves'];slots={i:collections.Counter()for i in range(53)}
 for line in gzip.open(r/'pin_producer_join.jsonl.gz','rt'):
  g=json.loads(line)
  for c in g['consumers']:
   if c[0]<0 or ls[c[0]]['master']!='dsfd_vm_static_w0_payload'or c[1]!='i_data':continue
   slot=c[2]//128
   if g['status']=='ONE_DRIVER':
    d=g['drivers'][0];key=('TOP.'+d[1])if d[0]<0 else ls[d[0]]['path']+'.'+d[1]
   else:key=g['status']
   if g['status']=='ONE_DRIVER':
    sl=int(re.search(r'w0_payload\[(\d+)\]',ls[c[0]]['path'])[1]);offset=128*sl+c[2]%128
    if slot<16:assert d[:3]==[-1,'f_su_wqd',512*slot+offset],(slot,d,c)
    elif slot<24:assert d[:3]==[-1,'f_hc_wqd',512*(slot-16)+offset],(slot,d,c)
    elif 28<=slot<32:assert d[:3]==[-1,'f_mx_wqd',512*(slot-28)+offset],(slot,d,c)
    elif 24<=slot<28:
     assert ls[d[0]]['master']=='dsfd_vm_static_landing';assert d[1]==('o_d01'if slot<26 else'o_d23');assert d[2]==512*((slot-24)%2)+offset
    elif 32<=slot<44 or 48<=slot<52:
     lane=slot-32 if slot<44 else slot-36;assert ls[d[0]]['path']==f'dut.u_cap.lane[{lane}].u_x.u_t'and d[1]=='o_d'and d[2]==30+offset,(slot,d,c)
   slots[slot][key]+=1
 rows=[]
 for i,counts in slots.items():
  assert sum(counts.values())==512,(i,counts)
  expected='SU'+str(i)if i<16 else'HC'+str(i-16)if i<24 else'LANDING'+str(i-24)if i<28 else'MIX4_'+str(i-28)if i<32 else'CAPTURE'+str(i-32)if i<44 else'COLLECTIVE'+str(i-44)if i<48 else'CAPTURE'+str(i-36)if i<52 else'WFC'
  rows.append(dict(slot=i,source=expected,payload_bits=512,actual_producers=dict(counts)))
 (r/'write_source_map.json').write_text(json.dumps(dict(scope=iv['scope'],source_commit=iv['source_commit'],source_pack_static_assigned_bits=iv['static_alias_blocks'][0]['final_assigned_bits'],sources=rows,qualification='Exact source wiring only; raw external die pin locations and inline collective/WFC combinational/control producers remain physical dependencies.'),indent=1)+'\n');print('53source slots x512 payloadbits each verified')
if __name__=='__main__':main()
