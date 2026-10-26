import importlib.util,json,tempfile
from pathlib import Path
from types import SimpleNamespace
import bind,bind_timing
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('boot',ROOT/'physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py');boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)

def fixture(kind='int'):
 b=bind.Binder.__new__(bind.Binder);b.F=SimpleNamespace(cells=[SimpleNamespace(path='source',ports={'q':[1,2]}),SimpleNamespace(path='sink',ports={'d':[1,2]})]);b.sinks={(1,'d',0):('int',0,'q',0,2),(1,'d',1):('int',0,'q',1,2)};b.cpart={0:'p',1:'p'};b.intra_dly={'p':{(0,'q',2)}};b.errors=[];b.plan={'die':{'name':'test'}};b.bitpos={};b.bitcyc={};return b

def apply(b,original=2,landed=5):
 st={'stale':0};b._apply_inner([dict(id='INNER:p:sink.d<-source@2',sink='sink',source='source',sink_port='d',asbuilt=original,landed=landed)],b.cell_index(),st);return st

def test_inner_exact_api_and_pricing():
 b=fixture();assert 'internal' not in b.bus_groups();assert b.depth('sink','d')=={0:0,1:0}
 st=apply(b);assert st['inner']['changed_bits']==2;assert b.intra_dly=={'p':{(0,'q',5)}}
 v=b.timing_depths('sink','d');assert v[0]==dict(kind='intra',source='source',source_port='q',source_bit=0,asbuilt_stages=2,landed_stages=5);assert b.depth('sink','d')=={0:0,1:0}
 groups=b.bus_groups();assert len(groups['internal'])==1;assert groups['internal'][0]['sink_bits']==[[0,1]]
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'groups.json';p.write_text(json.dumps(groups));g=boot.Groups(p)
  try:g.require_inner_priced()
  except ValueError as e:assert 'Unpriced changed INNER' in str(e)
  else:raise AssertionError('missing-pricing mutant escaped')
  rows=g.find('sink','d','source','q');value,rec=boot.bound_value(2,rows,'actual_path');assert value==5 and rec['delta']==3
  g.require_inner_priced()
  # A wrong endpoint cannot accidentally claim that the changed edge was priced.
  g=boot.Groups(p);assert not g.find('sink','d','other')
  try:g.require_inner_priced()
  except ValueError:pass
  else:raise AssertionError('wrong-source mutant escaped')

def test_stale_inner_rejected():
 b=fixture();st=apply(b,original=3);assert st['stale']==1 and b.errors;assert b.timing_depths('sink','d')[0]['landed_stages']==2

def test_zero_delay_and_nested_logic():
 b=fixture();b.sinks[(1,'d',0)]=('or',(('int',0,'q',0,2),('strap','0')));apply(b,landed=0)
 v=b.timing_depths('sink','d')[0];assert v['kind']=='or' and v['inputs'][0]['landed_stages']==0 and v['inputs'][0]['asbuilt_stages']==2;assert b.intra_dly=={'p':set()}

def test_crossing_kind_and_legacy_depth():
 b=fixture();d=('x','srcpart',0,'q',0,4,'p',2);b.sinks={(1,'d',0):d,(1,'d',1):d};b.bitcyc={('srcpart','p',0,'q',0):11}
 assert b.depth('sink','d')=={0:13,1:13};v=b.timing_depths('sink','d')[0];assert v['kind']=='crossing' and v['asbuilt_stages']==4 and v['landed_stages']==13
