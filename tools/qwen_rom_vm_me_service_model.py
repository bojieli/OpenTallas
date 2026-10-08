#!/usr/bin/env python3
"""Compose captured ME requests with the existing serialized reference calendar.

This does not transfer protected four-bank service timings to a new bank map.
"""
import argparse,hashlib,json,sys
from collections import Counter
from pathlib import Path

def model(root,trace):
 sys.path.insert(0,str(root/'tools'))
 from qwen_rom_finite_vm_schedule import compile_frame,proposal
 reference=proposal(root)
 x=json.loads(trace.read_text());cache={};counts=Counter();read_peak=write_peak=fanout=0
 for edge in x['edges']:
  if not edge['me_clk_en']:continue
  index=edge['frame'];f=x['frames'][index]
  if not int(f['xre'],16) and not int(f['owe'],16):continue
  counts[index]+=1
  if index in cache:continue
  reads=[];writes=[]
  if int(f['xre'],16):
   a=int(f['xaddr'],16);mask=int(f['xre'],16)
   reads=[dict(source='VX',seat=i,address=(a>>(24*i))&0xffffff) for i in range(2048) if mask>>i&1]
  if int(f['owe'],16):
   a=int(f['oaddr'],16);mask=int(f['omask'],16);enable=int(f['owe'],16)
   writes=[dict(source='ME',seat=16*i+l,address=16*((a>>(24*i))&0xffffff)+l) for i in range(48) if enable>>i&1 for l in range(16) if mask>>(16*i+l)&1]
  row=compile_frame(reads,writes)
  fanout=max(fanout,row['maximum_same_scalar_reuse'])
  read_peak=max(read_peak,len(reads));write_peak=max(write_peak,len(writes))
  cache[index]={k:row[k] for k in ['read_seats','write_seats','distinct_read_scalars','maximum_same_scalar_reuse','unique_aligned_read_windows','current_adapter_window_misses','physical_write_batches','bank_write_batches','conservative_current_adapter_edges']}
 total=sum(counts[i]*v['conservative_current_adapter_edges'] for i,v in cache.items());active=sum(counts.values())
 perkind={}
 for k,pred in [('read',lambda v:v['read_seats']>0),('write',lambda v:v['write_seats']>0)]:
  selected=[(counts[i],v) for i,v in cache.items() if pred(v)]
  perkind[k]=dict(captured_edges=sum(n for n,v in selected),service_edges=sum(n*v['conservative_current_adapter_edges'] for n,v in selected),single_edge_costs=sorted({v['conservative_current_adapter_edges'] for n,v in selected}))
 return dict(schema='opentallas.qwen-vm-native-me-service-cost.v1',
  source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['tools/qwen_rom_finite_vm_schedule.py','tools/qwen_rom_vm_me_service_model.py']},trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
  scope='Current-source captured W1 operation address schedule, no parent co-issue claim; all slots of original NR2256/NW865 source-ordered adapter counted',
  source_slots=dict(read=2256,write=865,active_read_peak=read_peak,active_write_peak=write_peak,
   read_request_address_enable_bits=2256*25,read_result_bits=2256*32,write_address_enable_data_bits=865*57,
   raw_scalar_frame_bits=(2256+865)*57,coded_scalar_frame_bits=(2256+865)*72,
   additional_epoch_owner_ack_publication_state='not included',
   measured_W1_max_scalar_fanout=fanout,
   broadcast='128 unique scalar reads serve2048 source slots:16 recipients/scalar. Native existingx topology supplies that duplication; a new provider must price and implement its scatter/holding registers; no uninstalled broadcast saving credited',
   write_priority='all reads from old frame; ME ascending port/lane, then MX, SU ascending lane, reducer, sequencer. Disabled source seats remain in existing walker cost; no dropped writes or reordered golden reductions'),
  serialized_reference=dict(actual_component_basis='Existing pinned finite four-bank controller calendar:9 read/28 postverified-write caller edges, plus walker/request/flush stages. Applies only to that existing serialized reference, not folded-bank option.',
   per_active_logical_edge_formula='4+2256+865+11*source_order_window_misses+30*ordered_masked_write_batches',
   active_native_edges=active,by_kind=perkind,reference_service_edges=total,
   conditional_extra_engine_edges=total-active,
   conditional_extra_at_833ps_ns=(total-active)*.833,
   composition_conditions=['All native producer/response/tag/collective clocks and finite debt obey one captured logical edge until ordered service and postverification finish','Non-ME requests absent only for this isolated component; source-current parent overlap may increase demand','Idle native edges advance once, not3125times; requires implemented empty-frame proof','No cross-edge cache reuse assumed'],
   measured_in_integrated_parent=False,full_token_extra=None),
  arithmetic_successor=dict(measured_write_retirement_delta_edges=55,bank_service_delta_separate=True,already_priced_by_existing_arithmetic_successor=True),
  baseline_frame_area_terms=reference['priced_component_terms'],
  next_implementable_bridge='Replay real native family calendars through captured logical-edge service and verify hold/resume, old-read-before-write and final ACK before granting source advancement. Final bank topology must follow all-family collision and captured-state/codec/crossing sizing.',
  ready_for_new_bank_RTL=False,physical_admission=False,adopted=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--trace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=model(a.root,a.trace);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['serialized_reference']['by_kind']))
