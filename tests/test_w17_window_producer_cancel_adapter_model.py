import importlib.util
from pathlib import Path
import sys
import pytest
p=Path(__file__).resolve().parents[1]/'tools/w17_window_producer_cancel_adapter_model.py'
s=importlib.util.spec_from_file_location('cancel_adapter',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
KW=dict(read_empty=True,selected_write_empty=True,delivery_fence=True,visibility_fence=True,provenance=True)

def full():
 a=m.Adapter(7);a.qe_accept()
 for _ in range(16):a.capture(7)
 a.qe_idle_receipt();return a

@pytest.mark.parametrize('prefix',range(17))
def test_fault_suffix_cannot_be_cancelled_early(prefix):
 a=m.Adapter(7);a.qe_accept()
 for _ in range(prefix):a.capture(7)
 a.fault()
 with pytest.raises(ValueError):a.cancel_local()
 for _ in range(16-prefix):a.capture(7)
 a.qe_idle_receipt();a.cancel_local()
 assert a.restart(**KW)==8
 assert a.discarded==16-prefix

@pytest.mark.parametrize('block',range(16))
def test_fault_preserves_accepted_WC_WS(block):
 a=full()
 for b in range(block+1):
  a.window_accept(b)
  if b<block:
   for kind in ('WC','WS'):
    ident=(7,b,kind);a.issue_write(ident);a.ack_write(ident)
   a.complete_block()
 a.fault();a.cancel_local()
 with pytest.raises(ValueError):a.restart(**KW)
 with pytest.raises(ValueError):a.complete_block()
 for kind in ('WC','WS'):
  ident=(7,block,kind);a.issue_write(ident);a.ack_write(ident)
 a.complete_block();assert a.restart(**KW)==8

@pytest.mark.parametrize('missing',list(KW))
def test_owner_empty_and_each_fence_are_independent(missing):
 a=full();a.fault();a.cancel_local();args=dict(KW);args[missing]=False
 with pytest.raises(ValueError):a.restart(**args)

def test_stale_duplicate_fault_edge_and_acked_not_visible():
 a=full();a.fault()
 with pytest.raises(ValueError):a.window_accept(0)
 with pytest.raises(ValueError):a.qe_accept()
 with pytest.raises(ValueError):a.capture(7)
 with pytest.raises(ValueError):a.capture(519)
 a.cancel_local()
 with pytest.raises(ValueError):a.restart(**dict(KW,visibility_fence=False))

def test_record_source_bound_and_not_implemented():
 r=m.record();assert len(r['boundary_witnesses'])==17
 assert r['WIN_STACK']==2 and r['status']=='MODEL_ONLY_UNIMPLEMENTED_NO_GO_NO_RTL'
