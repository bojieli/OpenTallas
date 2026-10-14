#!/usr/bin/env python3
"""Persistent source-exact transport regression, never a whole-token arithmetic claim."""
import argparse, ctypes as C, hashlib, json
from pathlib import Path
class Input(C.Structure):
 _fields_=[('data',(C.c_uint32*16)*8),('tag',C.c_uint64*8),('valid',C.c_uint8),('mode',C.c_uint8),('last',C.c_uint8),('rst_n',C.c_uint8)]
class Output(C.Structure):
 _fields_=[('data',(C.c_uint32*16)*8),('tag',C.c_uint64*8),('valid',C.c_uint8),('last',C.c_uint8),('err',C.c_uint8),('credit',C.c_uint8),('fault',C.c_uint8),('online',C.c_uint8),('drained',C.c_uint8),('rank',C.c_uint8*8),('fault_code',C.c_uint8*8),('credits',C.c_uint8*8),('cycle',C.c_uint64)]
def words(p):return [tuple((int(s,16)>>(32*l))&0xffffffff for l in range(16)) for s in p.read_text().splitlines() if s.strip()]
def identity(epoch,stage,token,pos,segment):return (epoch<<43)|(stage<<37)|(token<<19)|(pos<<6)|segment
p=argparse.ArgumentParser();p.add_argument('--lib',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--split',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
lib=C.CDLL(str(a.lib.resolve()));lib.native59_create.restype=C.c_void_p;lib.native59_destroy.argtypes=[C.c_void_p];lib.native59_tick.argtypes=[C.c_void_p,C.POINTER(Input),C.POINTER(Output)]
lib.native59_sample.argtypes=lib.native59_tick.argtypes;lib.native59_advance.argtypes=[C.c_void_p]
h=lib.native59_create();assert h
assert lib.native59_advance(h)==-4
ranks=[words(a.fixture/f'rank{r}.hex') for r in range(8)];gold=words(a.fixture/'expected.hex');credits=[32]*8
cycles=0;observed=0;quiet_delays=[];resets=0;operations=[]
def tick(i):
 global cycles
 o=Output()
 if a.split:
  assert lib.native59_sample(h,C.byref(i),C.byref(o))==0
  repeated=Output();assert lib.native59_sample(h,C.byref(i),C.byref(repeated))==0
  assert bytes(o)==bytes(repeated), 'repeated sample changed pre-edge state'
  assert lib.native59_advance(h)==0
  assert lib.native59_advance(h)==-4
 else:assert lib.native59_tick(h,C.byref(i),C.byref(o))==0
 cycles+=1
 for r in range(8):
  credits[r]+=bool(o.credit&(1<<r))-bool(i.valid&(1<<r))
  assert 0<=credits[r]<=32,(r,credits[r],cycles)
 return o
def empty(reset=False):
 i=Input();i.rst_n=not reset;return i
def reset():
 global resets
 for _ in range(4):tick(empty(True))
 credits[:]=[32]*8
 for _ in range(1000):
  o=tick(empty())
  if o.online==255 and o.drained==255:break
 else:raise AssertionError('actual reset release/drain did not complete')
 assert o.fault==0 and all(v==32 for v in o.credits)
 resets+=1

def operation(epoch,stage,segment,gather=False,nwords=256):
 global observed
 tag=identity(epoch,stage,151935,8191,segment);sent=[0]*8;received=[0]*8;start=cycles;last_cycle=None
 for relative in range(30000):
  i=empty();i.mode=255 if gather else 0
  for r in range(8):
   i.tag[r]=tag
   if sent[r]<nwords and credits[r] and relative>=r*3 and (relative+r)%5!=0:
    i.valid|=1<<r
    if sent[r]==nwords-1:i.last|=1<<r
    for l,value in enumerate(ranks[r][sent[r]]):i.data[r][l]=value
  o=tick(i);assert not o.fault,('fault',o.fault,list(o.fault_code),stage,segment,cycles)
  if i.valid or any(sent[r]*(8 if gather else 1)>received[r] for r in range(8)):assert o.drained!=255,('false drain',cycles)
  for r in range(8):
   if i.valid&(1<<r):sent[r]+=1
   if o.valid&(1<<r):
    k=received[r];total=nwords*(8 if gather else 1)
    assert k<total and o.tag[r]==tag and not(o.err&(1<<r))
    expected=ranks[k%8][k//8] if gather else gold[k]
    assert tuple(o.data[r])==expected,('data',stage,segment,r,k)
    assert bool(o.last&(1<<r))==(k==total-1)
    if gather:assert o.rank[r]==k%8
    received[r]+=1;observed+=1
  if all(v==nwords*(8 if gather else 1) for v in received):
   last_cycle=cycles;break
 else:raise AssertionError('operation timeout')
 for _ in range(1000):
  o=tick(empty());assert not o.valid and not o.fault
  if o.drained==255:break
 else:raise AssertionError('queue/pipeline/credit drain timeout')
 assert all(v==32 for v in o.credits) and credits==[32]*8
 quiet_delays.append(cycles-last_cycle)
 operations.append({'epoch':epoch,'stage':stage,'segment':segment,'gather':gather,'words':nwords,'start':start,'last':last_cycle,'actual_drained':cycles})
reset()
# API cannot silently truncate a wider offered tag into another59-bit identity.
bad=empty();bad.valid=1;bad.tag[0]=1<<63;untouched=Output();before=cycles
assert lib.native59_tick(h,C.byref(bad),C.byref(untouched))==-3
assert tick(empty()).cycle==before
# One continuous model and reset cohort: 36 layers x O/down, then real eight-rank gather transport.
for layer in range(1,37):
 for segment in range(2):operation(42,layer,segment)
operation(42,37,0,True,1)
assert resets==1 and len(operations)==73
# Genuine pending partial/link state must forbid drain, even when every output is quiet.
for w in range(8):
 i=empty();i.valid=1;i.tag[0]=identity(43,1,151935,8191,0)
 for l,v in enumerate(ranks[0][w]):i.data[0][l]=v
 o=tick(i);assert o.drained!=255
for _ in range(100):
 o=tick(empty());assert o.drained!=255 and not o.valid and not o.fault
pending_credits=list(credits);assert pending_credits[0]<32
reset();operation(44,1,0,nwords=2)
# Actual mismatched participant input after warm reset, without replacing any DUT result.
for w in range(2):
 i=empty();i.valid=255;i.last=255 if w==1 else 0
 for r in range(8):
  i.tag[r]=identity(45 if r!=1 else 44,2,151935,8191,0)
  for l,v in enumerate(ranks[r][w]):i.data[r][l]=v
 tick(i)
faults=0;escapes=0
for _ in range(1000):
 o=tick(empty());faults|=o.fault;escapes+=o.valid.bit_count()
assert faults==255 and escapes==0 and o.drained!=255
lib.native59_destroy(h)
receipt={'scope':'PERSISTENT_REAL8_NATIVE59_TRANSPORT_COMPONENT_NOT_WHOLE_TOKEN_ARITHMETIC_OR_PHYSICAL','ok':True,'library_sha256':hashlib.sha256(a.lib.read_bytes()).hexdigest(),'high_tag_bits_rejected_without_tick':True,'initial_reset_cohorts_for73operations':1,'operations':operations,'observed_words':observed,'cycles':cycles,'drain_delay_min':min(quiet_delays),'drain_delay_max':max(quiet_delays),'pending_partial_forbids_drain':True,'warm_reset_cancels_real_pending_state':True,'pending_credits_before_reset':pending_credits,'post_reset_epoch_mismatch_faults':faults,'poisoned_outputs':escapes,'clock_period_fs':833334,'LATU':14,'LATS':40,'BPC':3600,'identity_offer_not_allocator_acceptance':True}
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PASS persistent native59: 72 decoder collectives + head gather without reset; real queue/pipeline/credit drain; warm reset and stale epoch rejection')
