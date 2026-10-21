#!/usr/bin/env python3
"""Map separately sealed TOKEN fixture books into the connected source bench.
No production phase, stage programme anchor or physical delivery is inferred.
"""
from pathlib import Path
import argparse,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mode',type=int,default=0);a=p.parse_args()
x=json.loads(a.vectors.read_text());root=Path(__file__).resolve().parents[3]
assert x['status']=='TEST_COMPONENT_VECTORS_ONLY_UNEXECUTED'
assert x['source']['adapter_sha256']==hashlib.sha256((root/'rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_rx.sv').read_bytes()).hexdigest()
assert x['context']==dict(stage_id=1,rank=0,transaction_id=37,user=0,position=1048575,token=16754,epoch_identity=0x1021,programme_id64=0xf1c617d9224a57bf)
assert not x['full_stage'] and not x['full_token'] and not x['global_phase_qualified']
N=7000 if a.mode==0 else 200
v={k:[0]*(N+1) for k in ('events','ordinary','transit','book','expected0','expected1','expectedks')}
def ring(raw):return (raw<<21)|(1<<4)|(6<<1)|1
pairs=x['triples'] if a.mode==0 else x['triples'][:1]
for z in pairs:
 s=z['slots'];h=s['head_header_edge'];b=s['head_body_edge'];dh=s['receiver_header_edge'];db=s['receiver_body_capture_edge'];raw=int(z['raw_body512'],16);header=int(z['header512'],16)
 assert s['transit'][0]['receiver_header_edge']==h and s['transit'][0]['header_slot']==h and s['transit'][0]['transit_body_edge']==b
 assert (h,b,dh,db)==(100+16*z['index'],104+16*z['index'],103+16*z['index'],107+16*z['index'])
 if a.mode==1:raw^=1<<300
 if a.mode==2:header^=1<<130
 if a.mode==4:header^=1<<162
 v['events'][h]=ring(header);v['transit'][h]=b;v['book'][h]|=1;v['book'][dh]|=2;v['book'][h+1]|=4
 if a.mode!=3:v['events'][b]=ring(raw);v['book'][b+1]|=4
 if a.mode==0:v['expected1'][db+2]=int(z['legacy515'],16)
if a.mode==0:
 k=x['ks_slots'];h=k['head_edge'];d=k['receiver_edge']
 # The sealed last record is the independently checked KS descriptor header.
 rec=x['records'][-1];raw=int(rec['payload512'],16)
 v['events'][h]=ring(raw);v['book'][h]|=1;v['book'][h+1]|=4;v['book'][d]|=2
 v['expectedks'][d]=int(x['ks53'],16)
 # Same-cycle ordinary payload bypass, including nonzero inactive-side bits.
 for c in (60,80,N-30):v['ordinary'][c]=((1<<1103)|(0x123456789abcdef<<25)|(2<<1)|1)
a.out.mkdir(parents=True,exist_ok=False)
width={'events':276,'ordinary':276,'transit':12,'book':1,'expected0':129,'expected1':129,'expectedks':14}
for k,rows in v.items():(a.out/(k+'.memh')).write_text(''.join(f'{n:0{width[k]}x}\n' for n in rows))
(a.out/'metadata.json').write_text(json.dumps(dict(scope='UNEXECUTED_COMPONENT_TEST_ONLY',mode=a.mode,stop=N,vector_sha256=hashlib.sha256(a.vectors.read_bytes()).hexdigest(),source=x['source'],slotbooks='Explicit independently declared commonclock TEST books; no production mapping',expected_host=417 if a.mode==0 else 0),indent=2)+'\n')
print(N)
