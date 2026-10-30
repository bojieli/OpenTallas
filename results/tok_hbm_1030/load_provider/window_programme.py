"""Source-only two-buffer LOAD programme: explicit epochs and window-safe227 runs.

Dates, PHY completion and VM slot calendars are not assigned. Each adjacent
inserted LOAD batch may commute only when its VM destination ranges are disjoint.
Existing source body/drain/STORE ordering stays fixed. Effective227 descriptors
are split at every PC-window-half boundary, so buffer/epoch is constant per run.
"""
import argparse,collections,hashlib,json
from pathlib import Path
from window_fill_budget import windows


def key_at(address):
 s=(address&((1<<35)-1))>>5
 return(address>>35&3,s>>15,s>>8&15,((s>>6)^(s>>11)^(s>>16))&1)


def descriptor(src,dst,n):
 # Existing effective227: HBM U32 -> ordinary VM U32, unit steps,m1.
 if not 0<=dst<dst+n<=262144 or src%32 or dst%8 or n%8:raise ValueError('non-native split')
 return (5<<2)|(src<<5)|(1<<77)|(1<<93)|(5<<95)|(dst<<98)|(1<<170)|(1<<186)|(n<<206)


def compile_programme(packet):
 if packet['elision']['external_invalidations']:raise ValueError('unknown HBM mutation')
 versions=collections.Counter();ev=[];batch=[];splitcount=0
 def finish():
  nonlocal batch,splitcount
  if not batch:return
  spans=sorted(r['vm_words']for _,r in batch)
  if any(a[1]>b[0]for a,b in zip(spans,spans[1:])):raise ValueError('batch destination overlap: cannot commute')
  grouped=collections.defaultdict(list)
  for pos,r in batch:
   src,end=r['hbm_range'];dst=r['vm_words'][0]
   while src<end:
    stop=min(end,((src//2048)+1)*2048);n=(stop-src)//4;key=key_at(src)
    assert key_at(stop-1)==key
    grouped[key].append(dict(source_record=pos,source_byte=src,destination_word=dst,n=n,effective227=f'{descriptor(src,dst,n):057x}'))
    splitcount+=1;src=stop;dst+=n
  for key in sorted(grouped):ev.append(('read',(key,versions[key]),grouped[key]))
  batch=[]
 for pos,r in enumerate(packet['records']):
  if r['kind']=='load':batch.append((pos,r));continue
  finish()
  if r['kind']=='store':
   keys=tuple(sorted(windows(*r['hbm_range'])));ev.append(('write',keys,pos))
   for key in keys:versions[key]+=1
  else:ev.append(('anchor',pos,dict(stream_kind=r['kind'],source_record=r.get('source_record'),byte_offset=r['offset'],bytes=r['bytes'])))
 finish()
 future=collections.defaultdict(collections.deque)
 for pos,(kind,item,_)in enumerate(ev):
  if kind=='read':future[item].append(pos)
 cache=collections.defaultdict(dict);epochs=collections.Counter();out=[];counts=collections.Counter();digest=hashlib.sha256();samples=[]
 def emit(kind,**data):
  item=dict(kind=kind,**data);encoded=json.dumps(item,sort_keys=True,separators=(',',':')).encode();digest.update(encoded+b'\n');counts[kind]+=1
  if len(samples)<20:samples.append(item)
  out.append(item)
 def release(half,token,reason):
  slot,epoch=cache[half].pop(token);emit('release_all8',stack=half[0],half=half[1],buffer=slot,epoch=epoch,reason=reason)
 for pos,(kind,item,runs)in enumerate(ev):
  if kind=='anchor':
   emit('unchanged_source_anchor',record=item,**runs);continue
  if kind=='write':
   emit('source_store_anchor',record=runs)
   for key in item:
    half=(key[0],key[3])
    for token in list(cache[half]):
     if token[0]==key:release(half,token,'backing_store_invalidates')
   continue
  token=item;key,version=token;half=(key[0],key[3]);future[token].popleft()
  if token not in cache[half]:
   if len(cache[half])==2:
    victim=max(cache[half],key=lambda t:future[t][0]if future[t]else float('inf'));release(half,victim,'capacity_farthest_future')
   used={slot for slot,epoch in cache[half].values()};slot=next(s for s in range(2)if s not in used);epochs[half]+=1;epoch=epochs[half]
   if epoch>=65536:raise ValueError('epoch reuse needs defined wrap/drain contract')
   cache[half][token]=(slot,epoch);emit('begin_fill_all8',stack=key[0],half=key[3],buffer=slot,epoch=epoch,row=key[1],col=key[2],HBMbytes=32768)
  else:counts['window_hit']+=1
  slot,epoch=cache[half][token]
  for run in runs:
   sector=(run['source_byte']&((1<<35)-1))>>5;w=run['destination_word']
   route=dict(source_sector_start=sector,sector_count=run['n']//8,first_source_PC=((sector>>2)^(sector>>7)^(sector>>12))&31,first_destination_bank=(w>>3)&7,first_destination_quad=(w>>16)&3,source_PC_formula='((s>>2)^(s>>7)^(s>>12))&31 where s=source_sector_start+j',destination_bank_formula='((destination_word+8*j)>>3)&7',destination_quad_formula='(destination_word+8*j)>>16; j=0..sector_count-1')
   emit('load227',window_bundle=pos,stack=key[0],half=key[3],buffer=slot,epoch=epoch,row=key[1],col=key[2],route=route,**run)
 for half,resident in cache.items():
  for token in list(resident):release(half,token,'terminal_cleanup')
 assert counts['begin_fill_all8']==counts['release_all8']
 words=sum(x['n']for x in out if x['kind']=='load227')
 assert words==sum((r['hbm_range'][1]-r['hbm_range'][0])//4 for r in packet['records']if r['kind']=='load')
 return out,dict(status='SOURCE_ONLY_WINDOW_SAFE_PROGRAMME_NO_DATES_OR_PROVIDER_ADOPTION',counts=dict(counts),original_LOAD_descriptors=sum(r['kind']=='load'for r in packet['records']),window_safe_descriptors=splitcount,VMwords=words,serial_wordcounter_issue_plus_setup_cycles=words+splitcount,HBM_fill_bytes=32768*counts['begin_fill_all8'],programme_sha256=digest.hexdigest(),sample_events=samples,symbolic_dependencies=['all8 begin precedes actual tagged/epoch-matching PHY fill complete for that window','counter setup then each fixed datedstep requires owned filled matching perstep row/col/buffer/epoch','each LOAD227 laststep precedes actual last VMcommit/done through measured counter+leaf+face+bank latency','all preceding batch LOAD commits precede unchanged source body/drain anchor; source original waits and STREAM coupling retained','source STORE actual completion precedes window invalidation release; no old epoch may hit after that store','last actual VMconsumer precedes all8leafrelease; release completion precedes reuse begin of samebuffer','source anchor byte offsets identify original unchanged raw command, not an invented duration or new blanket fence'],parallel_issue_assumed=False,holds=['no physical fill/commit/done dates or target/slot calendar','source stack3 coverage and scratch authority open','original dynamic LOADs and numeric RTL/G5 excluded','begin/fill must complete before dated firststep; release after actuallastconsumer, not merely counter issue'])


def validate(events,packet):
 owned={};coverage=collections.defaultdict(list);anchors=[];checks=0
 for e in events:
  kind=e['kind']
  if kind in('source_store_anchor','unchanged_source_anchor'):anchors.append(e['record']);continue
  slot=(e['stack'],e['half'],e['buffer'])
  if kind=='begin_fill_all8':
   assert slot not in owned,'begin before release';owned[slot]=(e['epoch'],e['row'],e['col']);continue
  assert slot in owned and owned[slot][0]==e['epoch'],'unowned or stale epoch'
  if kind=='release_all8':del owned[slot];continue
  assert kind=='load227' and owned[slot]==(e['epoch'],e['row'],e['col'])
  r=packet['records'][e['source_record']];src=e['source_byte'];n=e['n'];dst=e['destination_word'];a,b=r['hbm_range']
  assert r['kind']=='load' and a<=src<src+n*4<=b
  assert dst==r['vm_words'][0]+(src-a)//4,'wrong source-to-VM mapping'
  assert key_at(src)==key_at(src+n*4-1)==(e['stack'],e['row'],e['col'],e['half'])
  assert int(e['effective227'],16)==descriptor(src,dst,n),'effective descriptor mismatch'
  sec=(src&((1<<35)-1))>>5
  assert e['route']['first_source_PC']==((sec>>2)^(sec>>7)^(sec>>12))&31,'wrong PC route'
  assert e['route']['first_destination_bank']==(dst>>3)&7
  assert e['route']['first_destination_quad']==dst>>16
  coverage[e['source_record']].append((src,src+n*4));checks+=1
 assert not owned,'terminal release missing'
 assert anchors==[i for i,r in enumerate(packet['records'])if r['kind']!='load'],'body/STORE/drain order changed'
 for i,r in enumerate(packet['records']):
  if r['kind']!='load':continue
  cursor=r['hbm_range'][0]
  for a,b in sorted(coverage[i]):assert a==cursor,'missing or duplicate source LOAD';cursor=b
  assert cursor==r['hbm_range'][1],'incomplete source LOAD'
 return checks


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--program-out',type=Path);a=ap.parse_args();base=Path(__file__).parents[1]
 packet=json.loads((base/'canonical_resident_cached/stream.json').read_text());events,report=compile_programme(packet)
 report['address_ownership_route_checks']=validate(events,packet)
 controls=[];li=next(i for i,e in enumerate(events)if e['kind']=='load227')
 for name,field,value in[('stale_epoch','epoch',events[li]['epoch']+1),('wrong_VM_destination','destination_word',events[li]['destination_word']+8)]:
  bad=list(events);bad[li]=dict(events[li]);bad[li][field]=value
  try:validate(bad,packet)
  except AssertionError:controls.append(name)
  else:raise AssertionError('mutant escaped:'+name)
 bad=[e for i,e in enumerate(events)if i!=next(j for j,x in enumerate(events)if x['kind']=='release_all8')]
 try:validate(bad,packet)
 except AssertionError:controls.append('missing_release')
 else:raise AssertionError('missing release escaped')
 report['controls_caught']=controls
 c=report['serial_wordcounter_issue_plus_setup_cycles'];report['serial_wordcounter_issue_setup_at833ps_ms']=c*833e-9
 report['existing_count8_sector_commands_if_proven_coalescing']=report['VMwords']//8
 report['conditional_coalesced_issue_setup_cycles']=report['VMwords']//8+report['window_safe_descriptors']
 report['conditional_coalesced_issue_setup_at833ps_ms']=report['conditional_coalesced_issue_setup_cycles']*833e-9
 report['coalescing_qualification']='Not current counter. Requires proved existing count8 producer coalescing and real source PC/VM bank calendars; no parallel output assumed.'
 if a.program_out:a.program_out.write_text(json.dumps(events,separators=(',',':'))+'\n')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='sample_events'}))
