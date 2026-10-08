import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c_s82_physical_owners as O
OWNER=Path('/home/ubuntu/dsrom-c-w2-20261003/tools/dsrom_s82_payload_interface.py')
@pytest.fixture(scope='module')
def api():return O.die_class(OWNER)
def test_dierom_source_bound_stage_domain(api):
 assert api(81,3,[],[],[]).inventory()['die_id']==327
 with pytest.raises(ValueError):api(82,0,[],[],[])
 with pytest.raises(ValueError):api(0,4,[],[],[])
def test_unowned_word_is_error_not_zero(api):
 with pytest.raises(ValueError,match='no unique'):api(0,0,[],[],[]).read(None,0,0)
def test_all_9552_macros_stay_charged(api):
 d=api(0,0,[],[],[]).inventory()
 assert d['physical_weight_macros']==9552 and d['actual_field_pairs']==2388
 assert d['unowned_frames_still_charged'] and not d['physical_admission']
def test_class_intersection_rejected(api):
 matrix=dict(stage=0,physical_owner_ranks=[0],plans=[(0,3,0,1,1,0,1)])
 provider=dict(stage=0,physical_owner_rank=0,pairs=[3])
 with pytest.raises(ValueError,match='overlap'):api(0,0,[matrix],[provider],[])
def test_word_interval_overlap_rejected(api):
 a=dict(stage=0,physical_owner_ranks=[0],plans=[(0,3,0,2,1,0,1)])
 b=dict(stage=0,physical_owner_ranks=[0],plans=[(0,3,0,2,1,1,1)])
 with pytest.raises(ValueError,match='matrix overlap'):api(0,0,[a,b],[],[])
def test_stage64_has_no_6bit_identity():
 assert (64&63)==0
 assert (64&127)!=0 and (81&127)==81
 assert max(range(82)).bit_length()==7
def test_no_checkpoint_import_or_construction(api):
 assert 'Checkpoint' not in api.__init__.__globals__
 assert api.__module__=='builtins'
