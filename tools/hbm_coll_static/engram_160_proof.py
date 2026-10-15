#!/usr/bin/env python3
"""Fixed 160-reservation successor model; no native successor RTL verdict.

Hash ownership changes payload identities/presence, never physical calendars.
Absent inner-present0 application NOP is a new typed protocol to implement;
it is distinct from an outer-valid0 transport idle.
"""
import argparse,copy,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from uarch_model_hcoll_rowgather import compile_calendar

def signature(c):
 return dict(hops=[tuple(h[k] for k in ('link','seq','slot','capture','write','read','accept','ordinal','receive')) for h in c['hops']],requests=[tuple(r[k] for k in ('home','local_slot','sector','cycle')) for r in c['requests']],reads=c['consumer_reads'],done=c['done'])
def prove(receipt,out):
 out.mkdir(parents=True,exist_ok=True);baseline=None;checks=[]
 for layer in [1,14]:
  from engram_compile import lower
  selected=compile_calendar(receipt,layer,two_rate=True);words,selected_limit=lower(selected)
  assert selected_limit==2424 and selected['done']==2833
  for n,code in enumerate(words):
   path=pathlib.Path(__file__).resolve().parents[2]/f'results/arch/hcoll_engram_rowgather_1015/program/layer{layer}/n{n}.hex'
   if path.exists():assert path.read_text()==''.join(f'{w:064x}\n' for w in code)
  cal=compile_calendar(receipt,layer,two_rate=True,local_slots=True)
  assert len(cal['hops'])==720 and cal['packets']==160 and len(cal['consumer_writes'])==216
  assert len({(w['row'],w['sector']) for w in cal['consumer_writes']})==216
  sig=signature(cal)
  if baseline is None:baseline=sig
  else:assert sig==baseline
  (out/f'layer{layer}.json').write_text(json.dumps(cal,indent=2)+'\n')
  # These numerical ownership variants test that the compiler never uses
  # selected presence/global rows to move any fixed resource reservation.
  for shift in range(8):
   r=copy.deepcopy(receipt);owners=[]
   for home,count in enumerate([4,4,4,4,3,2,2,1]):owners +=[(home+shift)%8]*count
   for row,owner in zip([x for x in r['rows'] if x['layer']==layer],owners):row['rank']=(0 if layer==1 else 8)+owner
   c=compile_calendar(r,layer,two_rate=True,local_slots=True);assert signature(c)==sig
   checks.append(dict(layer=layer,shift=shift,counts=[owners.count(h) for h in range(8)],done=c['done']))
  # Fifth local row violates the actual released interval bound, never waits.
  r=copy.deepcopy(receipt);rows=[x for x in r['rows'] if x['layer']==layer]
  for row in rows[:5]:row['rank']=(0 if layer==1 else 8)
  try:compile_calendar(r,layer,two_rate=True,local_slots=True)
  except AssertionError:pass
  else:raise AssertionError('fifth-owned-row mutant escaped')
 c=cal;limit=c['consumer_reads'][-1]['cycle']-406+1;banks=(limit+127)//128
 assert c['done']==2978 and limit==2569 and banks==21
 lastword=max((613*(h['ordinal']+1)+486)//487-1 for h in c['hops']);assert lastword<2048
 report=dict(status='PRE_RTL_FIXED_RESOURCE_CALENDAR_PASS',logical_rows=24,logical_sectors=216,physical_packets=160,selected_payloads=120,selected_application_NOPS=40,all_token_payload_count=120,hops=720,done_core_edges=c['done'],first_control_consumer=406,control_operations=limit,required_native_banks_per_node=banks,nodes=9,programme_native_banks=banks*9,largest_frame_ordinal=max(h['ordinal'] for h in c['hops']),last_physical_word=lastword,finite_words=2048,decode_continues_after_window=True,ownership_variant_checks=checks,fifth_owned_row_mutant='rejected',protocol='new typed inner-present0 application-NOP; outer613 valid/sequence remains active',native_successor_proven=False,physical_qualified=False,normative_unchanged_programme=False,source_sha256=hashlib.sha256(pathlib.Path(__file__).resolve().parents[1].joinpath('uarch_model_hcoll_rowgather.py').read_bytes()).hexdigest())
 (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('receipt',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);a=p.parse_args();prove(json.loads(a.receipt.read_text()),a.out)
