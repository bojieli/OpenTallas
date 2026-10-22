"""Emit real source fills and checks for the existing r010 gain consumer cut.

Arguments: emitted DS L0 directory, actual source-byte directory, fixture L00,
output directory. This is a component subset; other quarters remain open.
"""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from dma_load_1021 import lower_load,vmfc_release_word
root=Path(sys.argv[1]); source=Path(sys.argv[2]);fixture=Path(sys.argv[3]); out=Path(sys.argv[4]);out.mkdir(parents=True,exist_ok=True)
recordfile=root/'images/r010_su/record.json'
record=json.loads(recordfile.read_text());mapping={}
for sector,words in record['preload'].items():
 for index,w in enumerate(words):mapping[int(w)]=(0,int(sector),index)
f=json.loads((fixture/'records.json').read_text())['records']['0']; r=next(r for r in f if r['op']=='DMA.LOAD' and r['tag']=='q_norm.gain');a,o=r['desc']['A'],r['desc']['O']
metadata=json.loads((source/'sources.json').read_text());s=next(s for s in metadata['records'] if s['layer']==0 and s['tag']==r['tag']);raw=(source/s['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['inputs']['A']['sha256']
expected=np.load(fixture/'operands.npz')[r['outputs']['O']['array']]
assert hashlib.sha256(np.ascontiguousarray(expected).tobytes()).hexdigest()==r['outputs']['O']['sha256']
chunks=[];index=0
while index<o[1]:
 if o[0]+index not in mapping:index+=1;continue
 n=1
 while index+n<o[1] and o[0]+index+n in mapping:n+=1
 aa=[a[0]+index*2,n,1,0,1,'HBM','BF16'];oo=[o[0]+index,n,1,0,1,'VM','FP32']
 chunks+=lower_load(aa,oo,lambda w:mapping[w])['operations'];index+=n
windows={}
for op in chunks:windows.setdefault(tuple(op['window']),[]).append(op)
result=[]
for wi,(key,ops) in enumerate(windows.items()):
 q,row,col=key;epoch=wi+1;fills=[];loads=[]
 for lane in range(8):
  for group in range(2):
   pc=(q%2)*16+group*8+(lane//4)*4+lane%4
   for slot in range(64):
    j,b=slot>>2,slot&3;bhi=j&7;cc=(col<<1)|(j>>3);h=pc^cc^(((row&3)<<3)|bhi)
    sec=(row<<15)|(bhi<<12)|(cc<<7)|(h<<2)|b
    address=((q//2)<<35)+(sec<<5)
    data=bytes(raw[address+k-a[0]] if 0<=address+k-a[0]<len(raw) else 0 for k in range(32))
    fills.append(dict(lane=lane,group=group,slot=slot,bank=0,epoch=epoch,data=f'{int.from_bytes(data,"little"):064x}'))
 for op in ops:
  # Re-encode source epoch for this window; no release before the final read.
  fields=dict(op['fields'],epoch=epoch)
  from dma_load_1021 import load_word
  cmd=load_word(**fields);data=0;mask=0
  for j in range(fields['count']):
   logical=op['logical_word']+j;word=fields['word']+j
   source_index=2*(logical-o[0])
   assert int.from_bytes(raw[source_index:source_index+2],'little')<<16==int(expected[logical-o[0]])
   data|=int(expected[logical-o[0]])<<(32*word);mask|=1<<word
  packet=(1<<280)|(fields['sector']<<264)|(data<<8)|mask
  loads.append(dict(lane=op['source']['lane'],command=f'{cmd:016x}',logical_word=op['logical_word'],count=fields['count'],
          expected281=f'{packet:071x}',comparison='valid+sector+mask+onlymaskeddata',destq=fields['destq'],destbank=fields['destbank']))
 result.append(dict(sourceq=q,row=row,col=col,bank=0,epoch=epoch,fills=fills,loads=loads,
     release_all_payload159=f'{vmfc_release_word(255,bank=0,epoch=epoch):040x}'))
meta=dict(schema='opentallas.actual_dma_load_vectors.v1',scope='r15 actual next-SU consumer subset',qualifies_layer=False,
 source_sha256=s['sha256'],consumer_file=str(recordfile),consumer_sha256=hashlib.sha256(recordfile.read_bytes()).hexdigest(),
 fixture_expected_array=r['outputs']['O']['array'],fixture_expected_sha256=r['outputs']['O']['sha256'],full_record_words=o[1],
 selected_words=sum(v['count'] for w in result for v in w['loads']),packet_count=sum(len(w['loads']) for w in result),
 windows=result,note='Off-chip unrelated source bytes modelled zero; every selected LOAD source byte is released-checkpoint data, never output-derived. Readiness and routing remain hardware obligations.')
(out/'qnorm384.json').write_text(json.dumps(meta,indent=1)+'\n');print('DMA_QNORM_VECTORS',meta['selected_words'],meta['packet_count'],len(result))
