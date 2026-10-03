import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_layer_entry_state as M


def fixture():
 a={'h_in':np.ones((4,5120),dtype=np.float32),'pre_in':np.array([1,0,0,0],dtype=np.float32),
    'win':np.zeros((3,512),dtype=np.float32),'ckv':np.zeros((1,512),dtype=np.float32),'ik':np.zeros((1,128),dtype=np.float32),'open_group':np.zeros((1,2,512),dtype=np.float32)}
 r={'layer':7,'position':3,'kv_source_layer':2,'window_positions':[0,1,2],'compressed_row_ids':[0],'open_group_positions':[2],
    'input_sha256':M.digest(a['h_in'],a['pre_in']), 'state_sha256':{k:M.digest(a[k]) for k in ('win','ckv','ik','open_group')}}
 return a,r


def test_full_mhc_native_entry_beyond_L0_L20():
 a,r=fixture();v,w,report=M.entry(a,r)
 assert len(w)==20485 and v['ssx'][0]==20480
 assert report['layer']==7 and report['kv_source_layer']==2
 assert report['index_score_shape']==[1]
 assert v['ik'].shape==(1,128) and v['ckv'].shape==(1,512)


@pytest.mark.parametrize('defect',['missing_mix','wrong_h_shape','wrong_key_width','window_gap','duplicate_global','wrong_digest','float64','missing_open_group','wrong_KV_owner','wrong_cadence'])
def test_refuse_incomplete_or_invented_entry(defect):
 a,r=fixture()
 if defect=='missing_mix':a.pop('pre_in')
 if defect=='wrong_h_shape':a['h_in']=a['h_in'].reshape(20480)
 if defect=='wrong_key_width':a['ik']=np.zeros((2,512),dtype=np.float32)
 if defect=='window_gap':r['window_positions']=[0,2,3]
 if defect=='duplicate_global':r['compressed_row_ids']=[0,0]
 if defect=='wrong_digest':r['input_sha256']='bad'
 if defect=='missing_open_group':a.pop('open_group')
 if defect=='wrong_KV_owner':r['kv_source_layer']=6
 if defect=='wrong_cadence':a['ckv']=np.zeros((2,512),dtype=np.float32);a['ik']=np.zeros((2,128),dtype=np.float32)
 if defect=='float64':a['win']=a['win'].astype(np.float64)
 with pytest.raises(ValueError):M.entry(a,r)


def test_entry_reserves_current_window_row_not_129_rows():
 a,r=fixture();r['position']=130
 a['win']=np.zeros((127,512),dtype=np.float32)
 a['ckv']=np.zeros((65,512),dtype=np.float32);a['ik']=np.zeros((65,128),dtype=np.float32)
 a['open_group']=np.zeros((0,2,512),dtype=np.float32)
 r['window_positions']=list(range(3,130));r['compressed_row_ids']=list(range(65));r['open_group_positions']=[]
 r['state_sha256']={k:M.digest(a[k]) for k in ('win','ckv','ik','open_group')}
 assert M.entry(a,r)[2]['window_rows']==127
 a['win']=np.zeros((128,512),dtype=np.float32);r['window_positions']=list(range(2,130));r['state_sha256']['win']=M.digest(a['win'])
 with pytest.raises(ValueError,match='window capacity'):M.entry(a,r)


def test_bool_identity_is_not_global_row_zero():
 a,r=fixture();r['compressed_row_ids']=[False]
 with pytest.raises(ValueError,match='typed nonnegative'):M.entry(a,r)
