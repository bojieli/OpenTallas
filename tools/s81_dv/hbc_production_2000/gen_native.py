#!/usr/bin/env python3
"""Convert exact native compiler packets to receiver vectors, without rewriting dates/payloads."""
import hashlib,json,sys
from pathlib import Path
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
manifest={}
for case in ['A','B']:
 path=source/f'{case}.json';d=json.loads(path.read_text());seed=d['hbc']['fields']['local_epoch_at_config_body_capture'];body_edge=d['hbc']['records'][1]['receiver_boot_capture_edge']
 records=[(r['receiver_boot_capture_edge'],int(r['payload512'],16))for r in d['hbc']['records']]
 records.extend((p['receiver_capture_edge']-seed+body_edge,int(p['payload512'],16))for p in d['packets'])
 assert len({e for e,p in records})==len(records)
 records.sort()
 (out/f'{case}.ring.memh').write_text(''.join(f'{e:012x}{p:0128x}\n'for e,p in records))
 expected=[];headers={}
 for p in d['packets']:
  if p['opcode']=='HOST_WORD':
   if p['part']==0:headers[p['word_index']]=int(p['payload512'],16)
   else:
    cls=(headers[p['word_index']]>>76)&3;word=(cls<<513)|(int(p['payload512'],16)<<1)|1
    expected.append((p['receiver_capture_edge']+4,word))
 (out/f'{case}.host.memh').write_text(''.join(f'{(e<<515)|word:0141x}\n'for e,word in expected))
 ks=[p for p in d['packets']if p['opcode']=='KS_DESCRIPTOR'];assert len(ks)==1
 count=d['hbc']['fields']['HOST_word_count'];assert count==len(expected)
 manifest[case]=dict(input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),records=len(records),host_words=count,ks_edge=ks[0]['receiver_capture_edge']+2,ks53=d['ks53'],stage=d['context']['stage_id'],receiver_finish=d['seq_END_command']+10,seed=seed,body_boot_edge=body_edge)
 (out/f'{case}.meta.memh').write_text(f"{count:012x}\n{ks[0]['receiver_capture_edge']+2:012x}\n{int(d['ks53'],16):014x}\n{d['seq_END_command']+10:012x}\n")
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
