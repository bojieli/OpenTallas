"""Actual native leaf tests; inputs are raw bits, expected words assertion-only."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path


class Input(C.Structure):
 _fields_=[(k,C.c_uint32) for k in 'reset_n he_go he_nout he_k he_wbase he_xbase he_obase he_m he_xps he_ops'.split()]+[
 ('he_w_data',C.c_uint32*64),('he_x_q',C.c_uint32*8),
 ('ssx_valid',C.c_uint32),('ssx_last',C.c_uint32),('ssx_x',C.c_uint32*256)]


class Output(C.Structure):
 _fields_=[(k,C.c_uint32) for k in 'he_ready he_idle he_fault he_w_re'.split()]+[
 ('he_w_addr',C.c_uint32*8),('he_x_re',C.c_uint32),('he_x_addr',C.c_uint32*8)]+[
 (k,C.c_uint32) for k in 'he_o_we he_o_addr he_o_mask'.split()]+[
 ('he_o_data',C.c_uint32*32)]+[(k,C.c_uint32) for k in 'ssx_we ssx_addr ssx_data ssx_busy ssx_fault'.split()]


def run(library,out):
 lib=C.CDLL(str(library.resolve()))
 lib.s81_native_he_bootstrap_create.restype=C.c_void_p
 lib.s81_native_he_bootstrap_destroy.argtypes=[C.c_void_p]
 for suffix in ('eval','rise','fall'):
  getattr(lib,'s81_native_he_bootstrap_'+suffix).argtypes=[C.c_void_p,C.POINTER(Input),C.POINTER(Output)]
 events=[]
 for bubbles in (False,True):
  leaf=lib.s81_native_he_bootstrap_create();i=Input();o=Output()
  def edge():
   lib.s81_native_he_bootstrap_eval(leaf,C.byref(i),C.byref(o))
   lib.s81_native_he_bootstrap_rise(leaf,C.byref(i),C.byref(o))
   lib.s81_native_he_bootstrap_fall(leaf,C.byref(i),C.byref(o))
  try:
   edge();edge();i.reset_n=1;edge()
   for b in range(80):
    i.ssx_valid=1;i.ssx_last=b==79
    for lane in range(256): i.ssx_x[lane]=0x3f800000
    edge()
    assert not o.ssx_fault
    if bubbles:
     i.ssx_valid=0;i.ssx_last=0;edge()
   i.ssx_valid=0;i.ssx_last=0
   for drain in range(256):
    edge()
    assert not o.ssx_fault
    if o.ssx_we:
     assert o.ssx_addr==40960 and o.ssx_data==0x46a00000
     events.append(dict(kind='actual_native_SSX',bubbles=bubbles,drain=drain,address=o.ssx_addr,bits=o.ssx_data));break
   else: raise AssertionError('missing full H native SSX')
   # Same native leaf, not expected activation reloaded into a next operator.
   # A direct fullshape HE boundary test supplies explicit synthetic BF16
   # inputs and FP32weights=1; target provider integration is a separate gate.
   i.he_nout=24;i.he_k=2560;i.he_obase=41024;i.he_m=1;i.he_go=1
   for n in range(64): i.he_w_data[n]=0x3f800000
   for n in range(8): i.he_x_q[n]=0x3f800000
   edge();i.he_go=0;writes=[]
   for cycle in range(12000):
    edge();assert not o.he_fault
    if o.he_o_we:
     assert o.he_o_mask==1 and o.he_o_addr==41024+len(writes) and o.he_o_data[0]==0x46a00000
     writes.append(dict(cycle=cycle,address=o.he_o_addr,bits=o.he_o_data[0]))
    if len(writes)==24 and o.he_idle: break
   assert len(writes)==24 and o.he_idle
   events.append(dict(kind='actual_native_fullshape_HE',bubbles=bubbles,writes=writes))
  finally: lib.s81_native_he_bootstrap_destroy(leaf)
 result=dict(status='PASS_ACTUAL_FULLSHAPE_NATIVE_HE_AND_SSX_COMPONENT',library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),events=events,
             source_payload_qualification=False,joined_VM_or_prefix=False,host_FP_arithmetic=False,
             scope='Raw syntheticones,20480 H words and24x20480 HE products; SSX bubbles; no source weight provider/cold VM publication claim')
 out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();run(a.library,a.out)
