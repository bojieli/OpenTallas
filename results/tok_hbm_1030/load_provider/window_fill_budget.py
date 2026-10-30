"""Actual inserted LOAD bytes versus conservative existing PC-window fill policy.

One prefetch batch = adjacent inserted LOADs before a source body. The compiler
may read each needed PC-window half once within that batch, then release it.
No cross-batch cache reuse or source-epoch assumption is made. This is a proposed
policy cost, not current provider execution or a whole MTP VERIFY programme rate.
"""
import json
from pathlib import Path


def windows(begin,end):
 # Byte ranges from native inserted U32 loads are whole sectors. Window col
 # is bits11:8 of stack-local sector; PC half is parity(s6,s11,s16).
 if begin%32 or end%32:raise ValueError('nonsector window fill budget')
 stack=begin>>35&3;lo=(begin&((1<<35)-1))>>5;hi=lo+(end-begin)//32
 if (end-1)>>35&3!=stack:raise ValueError('range crosses native stack')
 result=set()
 while lo<hi:
  stop=min(hi,(lo//256+1)*256);row=lo>>15;col=lo>>8&15;base=(lo>>11&1)^(lo>>16&1)
  first,last=lo//64,(stop-1)//64
  halves={base^(first&1)}if first==last else{0,1}
  result.update((stack,row,col,h)for h in halves);lo=stop
 return result


if __name__=='__main__':
 base=Path(__file__).parents[1];p=json.loads((base/'canonical_group_anchored/stream.json').read_text());batch=set();count=0;batches=0;bytes_=0;max_windows=0;stacks=set();samples=[]
 def finish():
  global batch,count,batches,max_windows
  if not batch:return
  count+=len(batch);batches+=1;max_windows=max(max_windows,len(batch));batch=set()
 for meta in p['records']:
  if meta['kind']=='load':
   begin,end=meta['hbm_range'];found=windows(begin,end);batch|=found;stacks|={v[0]for v in found};bytes_+=end-begin
  else:finish()
 finish();filled=count*32768
 # Cross-check the constant-time range partition against direct sector decode
 # on representative small/unaligned-to-window native sector ranges.
 for begin,n in[(0,1),(63,2),(255,2),(32760,32),(65535,256),(689012300,500)]:
  direct=set()
  for sector in range(begin,begin+n):direct.add((0,sector>>15,sector>>8&15,((sector>>6)^(sector>>11)^(sector>>16))&1))
  assert windows(begin*32,(begin+n)*32)==direct
 result=dict(status='CONSERVATIVE_PROPOSED_WINDOW_POLICY_NOT_CURRENT_EXECUTION',source='canonical_group_anchored inserted LOADs only',inserted_load_bytes=bytes_,prefetch_batches=batches,window_half_fills=count,max_window_halves_per_batch=max_windows,existing_NPC2_half_fill_bytes=32768,proposed_HBM_fill_bytes=filled,overfetch_ratio=filled/bytes_,source_stacks=sorted(stacks),current_selected_stack2_matches=stacks=={2},cache_between_batches=False,original_source_DMA_LOADs_included=False,calendar_or_cycle_price_assigned=False,holds=['source stack3 unselected; actual path supports stack2 only','dates/target/routing/PHYcompletion and scratch authority unresolved','possible cache reuse requires source-epoch invalidation proof, not a free discount'])
 result['programme_scope']=p.get('programme_scope',dict(kind='MTP_VERIFY',row_positions=6,rate_unit='programme_steps_per_second',accepted_outputs_data_dependent=True))
 Path(__file__).with_name('window_fill_budget.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
