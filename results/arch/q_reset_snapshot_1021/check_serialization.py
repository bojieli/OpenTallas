"""Bounded serialization checks only; never calls the full selected builder."""
from pathlib import Path
import hashlib
import json
import os
import pickle
import sys

B = Path(__file__).resolve().parent
S = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(B), str(S/'tools'), str(S/'results/arch/qwen_tp8_1012')]
from actual_geometry_snapshot import enabled_snapshot, ActualSnapshot
assert 'OT_Q_ACTUAL_SNAPSHOT' not in os.environ
assert enabled_snapshot() is None
out = B/'serialization_check'
snap = ActualSnapshot(out)
G = snap.load_generator(S/'tools/qwen_rom_fulldie_b3r2.py')
model = dict(die=dict(w=100,h=100),insts=[],buses=[],fault_emit=dict(late_unrepaired=['fixture']),fault_source_bit_contract=[])
import numpy as np
snap.late(model, {0:dict(bid='fixture',P0=(1,2),P1=(3,4),frames=[])}, {(0,0):[(0,0,100,100)]}, {}, {(12.96,6.48,True):(np.array([[1.,2.]]),None)}, {'fixture':'blocked'}, {(1.,2.):'W'}, {(1.,2.):(.024,0)})
assert G._rst_tree_build([], [], 100, 100, .432, 2.16) == ([], [], {}, [])
occ = G._RstOcc([(0,0,100,100)],100,100,.432,2.16)
N={0:dict(x=10,y=10,kids=[],sinks=[],outs=[])}
ht={0:0};bid='rst_fixture'
def new(tx,ty,box=None,_N=N,_seq=[0],_bid=bid):
    return occ.site(tx,ty,box)
def chain(k,lv):
    mst=G.RST_PAD;head=prev=None
    a=new(10,10)
    assert a is None
chain(0,1)
failure=pickle.load(open(out/'reset_pad_failure.pkl','rb'))
assert failure['site_parameters']['lim']==600
assert failure['occupied']==[(0,0,100,100)]
assert failure['context']['k']==0 and failure['context']['lv']==1
assert failure['new_context']['_bid']=='rst_fixture'
late=pickle.load(open(out/'late_graph.pkl','rb'))
assert late['sites'][(12.96,6.48,True)].tolist()==[[1.,2.]]
assert late['pt_face'][(1.,2.)]=='W'
manifest=json.load(open(out/'manifest.json'))
for row in manifest['files']:
    assert hashlib.sha256((out/row['name']).read_bytes()).hexdigest()==row['sha256']
try:
    snap.save('reset_pad_failure.pkl',dict(overwrite=True))
except AssertionError:
    pass
else:
    raise AssertionError('existing evidence overwritten')
assert hashlib.sha256((S/'tools/qwen_rom_fulldie_b3r2.py').read_bytes()).hexdigest()=='c5655b8dec117f2525c093b56348287a5f68577e0a74c9102122caed81e0fdd8'
assert failure['site_parameters']['w']==12.96 and failure['site_parameters']['h']==6.48
assert 'pops' in failure['search'] and failure['search']['best'] is None
print('SERIALIZATION_PASS disabled_noop actual_empty_builder blocked_actual_site capture_chain_context tuple_keys numpy_arrays hashes no_overwrite source_unchanged')
