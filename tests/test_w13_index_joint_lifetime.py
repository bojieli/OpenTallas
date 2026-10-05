import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w13_index_joint_lifetime as M

def test_phase_containment_nonoverlap_and_once_only_compose():
 d=M.build()
 for phase,regions in d['simultaneous_regions_by_phase'].items():
  a=sorted(regions.values())
  assert all(0<=x<y<=65536 for x,y in a)
  assert all(x[1]<=y[0] for x,y in zip(a,a[1:]))
  assert max(x[1] for x in a)==63488
 assert d['extra_vs_allF32_61440']['sum']==63488-61440
 assert not d['scratch_reuse_admission']['admitted']

def test_score_copy_bank_maps_and_runtime_null():
 d=M.build();dst=set()
 for e in d['ordinary_copy_events']:
  assert len({(e['source_word_base']+j)%32 for j in range(32)})==32
  assert len({(e['destination_word_base']+j)%32 for j in range(32)})==32
  dst.update(e['destination_word_base']+j for j in range(32))
  assert e['launch_tick'] is None and e['store_visible_tick'] is None
 assert dst==set(range(4096,12288))
 assert d['physical_admission']=='FAIL_CLOSED'
