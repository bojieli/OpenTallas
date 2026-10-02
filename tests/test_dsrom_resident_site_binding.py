import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_resident_site_binding as R

def words(fmt,begin,end,slot=0):
    return {'format':fmt,'begin':begin,'end':end,'logical_slot':slot,'owner':'synthetic-only','source_receipts':['synthetic-only']}

def sites():
    proof={'whole_element_hard_abstract_available':True,'rtl_source_receipts':['synthetic-only'],
           'abstract_source_receipts':['synthetic-only'],'RTL_params':{'BF16':1,'NB':2,'PP':1},
           'included_formats':['fp4','fp8','bf16'],'outline_um':[1002.89,142.56]}
    return [{'pair':0,'physical_class':'dual','dual_compute_proof':proof,'resident_words':[words('fp4',0,64),words('bf16',64,128)]},
            {'pair':1,'physical_class':'q','resident_words':[words('fp4',0,128)]}]

def test_mixed_residency_one_site_one_storage():
    x=R.validate(sites(),2,1)
    assert x['q_work_sites']==2 and x['BF_work_sites']==1 and x['mixed_work_sites']==1
    assert x['unique_resident_work_sites']==2 and x['physical4096_macros']==8
    assert x['resident_sites'][0]['occupied_words_both_slots']==128
    assert x['physical_frame_um2']==pytest.approx(207797.5944)

@pytest.mark.parametrize('mutation',['missing_abstract','q_on_BF','BF_on_q','overlap','depth','mask','duplicate','small_frame'])
def test_unsupported_provider_or_capacity_credit_refused(mutation):
    s=sites()
    if mutation=='missing_abstract':s[0]['dual_compute_proof']['whole_element_hard_abstract_available']=False
    elif mutation=='q_on_BF':s[0]['physical_class']='BF'
    elif mutation=='BF_on_q':s[1]['resident_words']=[words('bf16',0,64)]
    elif mutation=='overlap':s[0]['resident_words'][1]['begin']=32
    elif mutation=='depth':s[0]['resident_words'][1]['end']=8193
    elif mutation=='mask':s[1]['physical_class']='BF'
    elif mutation=='duplicate':s[1]['pair']=0
    else:s[0]['dual_compute_proof']['outline_um']=[510.84,126.9]
    with pytest.raises(ValueError):R.validate(s,2,1)

def test_actual_mask_not_active_mask():
    assert len(R.rtl_bf_sites(4096,724))==724
    assert R.rtl_bf_sites(8,2)=={0,4}


def test_source_class_aliases_do_not_bypass_physical_proof():
    s=sites();s[0]['physical_class']='BF_DUAL';s[1]['physical_class']='Q_ONLY'
    assert R.validate(s,2,1)['storage_capacity_counted_once']
    assert R.source_formats('BF_DUAL')=={'fp4','fp8','bf16'}
    s[0].pop('dual_compute_proof')
    with pytest.raises(ValueError):R.validate(s,2,1)

def test_padding_keeps_source_physical_class():
    c={'compiled_NP':4,'BF_DUAL_site_IDs':[0,2],'Q_ONLY_site_IDs':[1,3],'weight_active_site_IDs':[0,1],'padding_site_IDs':[2,3]}
    x=R.validate_site_ids(c,2)
    assert x['physical4096_macros']==16 and x['BF_DUAL_pairs']==2
    assert x['physical_frame_um2']==pytest.approx(2*(float(R.Q_FRAME)+float(R.BF_FRAME)))
    assert not x['physical_or_SSFF_qualification_transferred']

@pytest.mark.parametrize('fault',['mask','duplicate','padding_overlap','missing_padding'])
def test_site_id_faults_refused(fault):
    c={'compiled_NP':4,'BF_DUAL_site_IDs':[0,2],'Q_ONLY_site_IDs':[1,3],'weight_active_site_IDs':[0,1],'padding_site_IDs':[2,3]}
    if fault=='mask':c['BF_DUAL_site_IDs']=[0,1]
    elif fault=='duplicate':c['weight_active_site_IDs']=[0,0,1]
    elif fault=='padding_overlap':c['padding_site_IDs']=[1,2,3]
    else:c['padding_site_IDs']=[2]
    with pytest.raises(ValueError):R.validate_site_ids(c,2)
