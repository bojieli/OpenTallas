#!/usr/bin/env python3
"""Opaque-payload replay and service obligations, not bank RTL or timing evidence."""
import argparse, hashlib, json
from pathlib import Path
from collections import Counter,defaultdict

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fold(a,bits):
 w=a>>4;return ((w^(w>>bits))&((1<<bits)-1),w>>bits)
def initial(a):return (a*2654435761^0x76185429)&0xffffffff
def payload(pc,cycle,source,lane):return int.from_bytes(hashlib.sha256(f'{pc}:{cycle}:{source}:{lane}'.encode()).digest()[:4],'little')
def frame(e,pc):
 r=[(name,lane,a) for name in ('va','vb','vc') for lane,a in e['reads'].get(name,[])]
 w=[('su',lane,a,payload(pc,e['cycle'],'su',lane)) for lane,a in sorted(e['writes'])]
 if e['reducer'] is not None:w.append(('reducer',0,e['reducer'],payload(pc,e['cycle'],'reducer',0)))
 return r,w

def plan(reads,writes,bits):
 """Unique-word broadcast reads; per-bank source-ordered masked write batches."""
 rg=defaultdict(dict);wg=defaultdict(list)
 for src,lane,a in reads:
  bank,row=fold(a,bits);rg[bank].setdefault(row,dict(word=a>>4,targets=[]))['targets'].append((src,lane,a&15))
 for src,lane,a,data in writes:
  bank,row=fold(a,bits)
  if not wg[bank] or wg[bank][-1]['row']!=row:wg[bank].append(dict(row=row,word=a>>4,values={},sources=[]))
  batch=wg[bank][-1];batch['values'][a&15]=data;batch['sources'].append((src,lane,a&15))
 rr=max(map(len,rg.values()),default=0);ww=max(map(len,wg.values()),default=0)
 return rg,wg,rr,ww

class Memory:
 def __init__(self,bits):self.bits=bits;self.words={}
 def read(self,word):
  key=fold(word<<4,self.bits)
  if key not in self.words:self.words[key]=[initial((word<<4)+i) for i in range(16)]
  return self.words[key][:]
 def write(self,batch):
  arr=self.read(batch['word'])
  for lane,data in batch['values'].items():arr[lane]=data
  self.words[fold(batch['word']<<4,self.bits)]=arr
 def scalar(self,a):return self.read(a>>4)[a&15]

def replay(reads,writes,bits,memory,golden,mutant=None):
 expected={(s,l):golden.get(a,initial(a)) for s,l,a in reads}
 final={}
 for s,l,a,d in writes:final[a]=d
 rg,wg,rr,ww=plan(reads,list(reversed(writes)) if mutant=='reverse_writes' else writes,bits)
 actual={}
 def do_reads():
  for i in range(rr):
   for bank,rows in sorted(rg.items()):
    vals=list(rows.values())
    if i>=len(vals):continue
    request=vals[i];word=memory.read(request['word'])
    for s,l,offset in request['targets']:actual[s,l]=word[offset]
 def do_writes():
  for i in range(ww):
   for bank,batches in sorted(wg.items()):
    if i<len(batches):memory.write(batches[i])
 if mutant=='write_before_read':do_writes();do_reads()
 else:do_reads();do_writes()
 assert actual==expected,'read response differs from pre-edge snapshot'
 for a,d in final.items():assert memory.scalar(a)==d,'source-order last-writer priority differs'
 golden.update(final)
 for word in set(a>>4 for a in final):
  for lane in range(16):
   address=word*16+lane
   assert memory.scalar(address)==golden.get(address,initial(address)), 'partial write changed an unselected scalar'
 return dict(read_quanta=rr,write_quanta=ww,serial_barrier_quanta=rr+ww,
  unique_read_words=sum(map(len,rg.values())),ordered_write_batches=sum(map(len,wg.values())))

def describe(reads,writes,bits):
 mc=Counter(a for _,_,a in reads);wc=Counter(a>>4 for _,_,a in reads)
 rg,wg,rr,ww=plan(reads,writes,bits)
 ra=set(mc);wa=[a for _,_,a,_ in writes];su=set(a for s,_,a,_ in writes if s=='su');rd=set(a for s,_,a,_ in writes if s=='reducer')
 return dict(read_requests=len(reads),unique_read_scalars=len(mc),duplicate_scalar_read_requests=len(reads)-len(mc),max_scalar_read_fanout=max(mc.values(),default=0),unique_read_words=len(wc),max_word_read_fanout=max(wc.values(),default=0),write_requests=len(writes),unique_write_scalars=len(set(wa)),unique_write_words=len(set(a>>4 for a in wa)),scalar_read_write_aliases=len(ra&set(wa)),word_read_write_aliases=len(set(wc)&set(a>>4 for a in wa)),su_reducer_simultaneous=bool(su and rd),su_reducer_scalar_aliases=len(su&rd),su_reducer_word_aliases=len(set(a>>4 for a in su)&set(a>>4 for a in rd)),duplicate_scalar_writes=len(wa)-len(set(wa)),read_quanta=rr,write_quanta=ww,serial_barrier_quanta=rr+ww,
  read_row_conflict=rr>1,write_batch_conflict=ww>1)

def run(root,trace,out):
 out.mkdir(parents=True,exist_ok=True)
 sources=['results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/top.sv','rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vprm_stream4.sv','rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_checked_vm_bank.sv']
 pins={p:digest(root/p) for p in sources}
 for path in sources[:2]:
  text=(root/path).read_text()
  needles=['va_q[vi*32 +: 32] <= (a < VM_ELEMS) ? vm[a]', 'if (vw_su_we[vi]) begin a = vw_su_addr[vi*24 +: 24]; if (a < VM_ELEMS) vm[a] <= vw_su_data[vi*32 +: 32];', 'if (vw_rd_we && vw_rd_addr < VM_ELEMS) vm[vw_rd_addr] <= vw_rd_data;']
  assert all(n in text for n in needles),'source read/write semantics changed'
  assert text.index(needles[1])<text.index(needles[2]),'source writer priority changed'
 events=json.loads((trace/'events.json').read_text());summary=json.loads((trace/'summary.json').read_text())
 for path,pin in summary['source_sha256'].items():assert digest(root/path)==pin,('trace/source changed',path)
 result=dict(schema='opentallas.qwen-su-bank-service-obligations.v1',source_sha256=pins,trace_sha256={n:digest(trace/n) for n in ('events.json','summary.json')},configurations={})
 schedules={}
 for bits in (7,8):
  rows=[];checks=0;neg_found=False;total_quanta=0;by_pc={}
  for pc,ev in events.items():
   memory=Memory(bits);golden={};pcq=0
   for e in ev:
    reads,writes=frame(e,pc);m=describe(reads,writes,bits)
    if not neg_found and m['scalar_read_write_aliases']:
     # Mutant uses identical independent initial memory at this captured frame.
     try:replay(reads,writes,bits,Memory(bits),{},'write_before_read')
     except AssertionError:neg_found=True
     else:raise AssertionError('actual-alias write-first mutation survived')
    service=replay(reads,writes,bits,memory,golden);checks+=len(reads)+len(set(a for _,_,a,_ in writes));pcq+=service['serial_barrier_quanta'];rows.append(dict(pc=int(pc),cycle=e['cycle'],**m))
   by_pc[pc]=dict(active_frames=len(ev),abstract_service_quanta=pcq)
   total_quanta+=pcq
  assert neg_found
  # Synthetic obligation only: legal source seats sharing one scalar, reducer wins.
  a=6144;rs=[('va',0,a),('vb',63,a)];ws=[('su',0,a,0x11111111),('su',63,a,0x22222222),('reducer',0,a,0x33333333)]
  replay(rs,ws,bits,Memory(bits),{})
  try:replay(rs,ws,bits,Memory(bits),{},'reverse_writes')
  except AssertionError:priority_negative=True
  else:raise AssertionError('priority negative survived')
  metrics=[k for k in rows[0] if k not in ('pc','cycle')]
  peaks={k:max(r[k] for r in rows) for k in metrics}
  witnesses={k:next(dict(pc=r['pc'],cycle=r['cycle'],value=r[k]) for r in rows if r[k]==v) for k,v in peaks.items()}
  counts={k:sum(bool(r[k]) for r in rows) for k in ('scalar_read_write_aliases','word_read_write_aliases','su_reducer_simultaneous','su_reducer_scalar_aliases','su_reducer_word_aliases','duplicate_scalar_writes','read_row_conflict','write_batch_conflict')}
  result['configurations'][str(1<<bits)]=dict(fold_bits=bits,peaks=peaks,witnesses=witnesses,frame_counts=counts,per_pc=by_pc,abstract_service_quanta=total_quanta,opaque_scalar_checks=checks,negative_controls=dict(actual_alias_write_before_read='REJECTED',synthetic_duplicate_writer_reverse_priority='REJECTED'))
  schedules[str(1<<bits)]=rows
 result['scope']='14 independently reset static L20 SU operations only; source-bank bridge unimplemented. Opaque payloads exercise address/control ordering, not arithmetic. One bank transaction per abstract quantum, all read responses precede all writes, completion barrier releases source frame only after writes. Service quanta are NOT measured clock cycles: SRAM read/return, protection, write completion, mux, fanout, capture, source-hold and resume costs are unbound. No all-family temporal composition or final live-extent proof. Existing four-bank checked window provider does not implement these folded mappings.'
 result['source_frame_storage_lower_bound_bits']=dict(read_response_payload=192*32,scalar_write_payload=65*32,read_request_address_enable=192*25,write_request_address_enable=65*25,total=192*32+65*32+192*25+65*25,excluded='owner tags, protection/checks, conflict indices, request/return mux registers, FSM, bank data staging and all non-SU families; not a floorplan sizing result')
 (out/'model.json').write_text(json.dumps(result,indent=2)+'\n');(out/'edge_service.json').write_text(json.dumps(schedules,separators=(',',':'))+'\n')
 print(json.dumps({k:dict(peaks=v['peaks'],counts=v['frame_counts'],quanta=v['abstract_service_quanta'],checks=v['opaque_scalar_checks']) for k,v in result['configurations'].items()},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--trace',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();run(a.root,a.trace,a.out)
