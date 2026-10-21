#!/usr/bin/env python3
"""Read-only derive minimal context/book demand from the executed 417 fixture.
This cannot create production metadata or a runtime bootstrap image.
"""
import json,hashlib,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
x=json.loads(a.vectors.read_text());assert x['full_stage'] is False and x['global_phase_qualified'] is False
pairs=x['triples'];assert len(pairs)==417
contexts=set();strides={};book={}
for i,z in enumerate(pairs):
 h=int(z['header512'],16)
 contexts.add(tuple((h>>lo)&((1<<w)-1) for lo,w in [(40,8),(48,2),(50,16),(78,10),(88,21),(109,21),(130,32),(210,64)]))
 s=z['slots'];assert s['head_header_edge']==100+16*i and s['head_body_edge']==104+16*i
 assert s['receiver_header_edge']==103+16*i and s['receiver_body_capture_edge']==107+16*i
assert len(contexts)==1
for name,start in [('stage0_NEXT',100),('stage1_NEXT',103)]:
 book[name]=dict(header_first=start,header_stride=16,word_count=417,body_gap=4,headers_last=start+16*416,body_last=start+16*416+4)
book['stage0_NEXT']['KS_header']=6776;book['stage1_NEXT']['KS_header']=6779
book['PREV']=dict(source_TX_capture=6993,transit_RX_capture=6995,transit_TX_capture=6996,head_capture=6998,host_event_capture=6999,host_event_output=7000,actual_source_status_sample=6990,actual_source_return_send=6992)
# Every NEXT book access is before the first PREV access in this actual proof.
assert 6779<6993
fields=[('TID',16),('user',10),('position',21),('token',21),('epoch_identity',32),('programme_identity',64),('local_epoch_at_config_body_capture',48),('first_NEXT_header',48),('NEXT_header_stride',12),('HOST_word_count',10),('target_body_gap',8),('transit_body_gap',8),('KS_capture',48),('PREV_return_input_capture',48),('local_status_sample',48),('local_return_send',48),('expected_data_stage',8),('expected_data_rank',2),('flags',12)]
assert sum(w for _,w in fields)==512
bits=[];lo=0
for n,w in fields:bits.append(dict(name=n,lo=lo,width=w));lo+=w
r=dict(scope='EXECUTED_TEST_FIXTURE_DEMAND_ONLY_NOT_PRODUCTION',vectors_sha256=hashlib.sha256(a.vectors.read_bytes()).hexdigest(),actual_records=835,HOST_words=417,distinct_contexts=len(contexts),context=next(iter(contexts)),actual_KS_descriptors=1,distinct_users=1,programme_epoch_global_in_this_fixture=True,book=book,NEXT_PREV_simultaneous_reads=0,storage=dict(proposed_pattern_fields_bits=512,context_and_pattern_entries=1,indexed_context_array=False,source_payload_holds='finite one-context configuration plus shadow; no512-row capacity inferred',SRAM_selection='NONE; no storage RTL authorized, macro choice deferred until actual expanded selected programme demand'),schema=bits,bootstrap_header_body_dates='UNMEASURED/UNASSIGNED; no runtime image',production_global_stage_epoch_anchor='OPEN')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
