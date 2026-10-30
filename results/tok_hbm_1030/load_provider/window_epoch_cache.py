"""Static two-buffer NPC2 window reuse with real backing-write invalidations.

Policy estimate only. No runtime cache tags/allocator or target is introduced:
compile-time future use selects one of the existing two landing buffers. Every
STORE to a window changes its epoch; stale resident windows cannot hit.
"""
import collections,json
from pathlib import Path
from window_fill_budget import windows


def events(packet):
 if packet['elision']['external_invalidations']!=0:raise ValueError('unknown external HBM mutation needs explicit window epoch invalidation')
 version=collections.Counter();batch=set();out=[]
 def finish():
  nonlocal batch
  # Policy chooses a deterministic window order within one prefetch batch;
  # all operands must land before the unchanged following body starts.
  for key in sorted(batch):out.append(('read',(key,version[key])))
  batch=set()
 for rec in packet['records']:
  if rec['kind']=='load':batch|=windows(*rec['hbm_range'])
  else:
   finish()
   if rec['kind']=='store':
    keys=windows(*rec['hbm_range']);out.append(('write',tuple(sorted(keys))))
    for key in keys:version[key]+=1
 finish();return out


def price(ev,policy):
 future=collections.defaultdict(collections.deque)
 for pos,(kind,item)in enumerate(ev):
  if kind=='read':future[item].append(pos)
 cache=collections.defaultdict(dict);miss=hit=stale=evict=0;clock=0
 for pos,(kind,item)in enumerate(ev):
  clock+=1
  if kind=='write':
   for key in item:
    half=(key[0],key[3]);dead=[v for v in cache[half]if v[0]==key]
    for token in dead:del cache[half][token];stale+=1
   continue
  token=item;key,version=token;future[token].popleft();half=(key[0],key[3]);resident=cache[half]
  if token in resident:hit+=1;resident[token]=clock;continue
  miss+=1
  if len(resident)==2:
   if policy=='lru':victim=min(resident,key=lambda t:resident[t])
   else:victim=max(resident,key=lambda t:future[t][0]if future[t]else float('inf'))
   del resident[victim];evict+=1
  resident[token]=clock
 terminal=sum(len(v) for v in cache.values())
 assert stale+evict+terminal==miss, 'every acquired window must release exactly once'
 return dict(policy=policy,read_windows=miss+hit,fills=miss,hits=hit,invalidated_resident_windows=stale,capacity_evictions=evict,HBM_fill_bytes=miss*32768,release_broadcasts_at_least=stale+evict,terminal_release_broadcasts=terminal,total_release_broadcasts_with_terminal_cleanup=stale+evict+terminal,buffers_per_landing_half=2)


if __name__=='__main__':
 root=Path(__file__).parents[1];p=json.loads((root/'canonical_resident_cached/stream.json').read_text());ev=events(p);fresh=sum(kind=='read'for kind,item in ev);result=dict(status='EXISTING_TWO_BUFFER_POLICY_ESTIMATE_NO_INSTALL',source='canonical_resident_cached inserted LOADs only',fresh_window_fills=fresh,fresh_HBM_fill_bytes=fresh*32768,LRU=price(ev,'lru'),static_farthest_future=price(ev,'farthest_future'),actual_backing_store_events=sum(kind=='write'for kind,item in ev),external_native_write_rows_proven_disjoint=p['elision']['disjoint_external_write_rows'],source_stack3_current_provider_unselected=True,cycle_price_assigned=False,holds=['existing NPC2 landing buffers assumed; new provider architecture not adopted','actual fill/ownership/epoch/release calendars and backend routing still required','source numeric/G5/scratch authority open; converter bytes and original dynamic LOADs excluded'])
 # A write must refute an otherwise valid repeated-window hit.
 key=(3,0,0,0);control=price([('read',(key,0)),('write',(key,)),('read',(key,1))],'farthest_future');assert control['fills']==2 and control['hits']==0;result['stale_window_control']='CAUGHT_2fills_nohit';result['programme_scope']=p.get('programme_scope',dict(kind='MTP_VERIFY',row_positions=6,rate_unit='programme_steps_per_second',accepted_outputs_data_dependent=True))
 Path(__file__).with_name('window_epoch_cache.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
