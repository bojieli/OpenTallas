import copy
import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('review',Path(__file__).parents[1]/'tools/qc_engram_home_intake.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
@pytest.fixture(scope='module')
def metadata():return P.metadata()
def test_independent_geometry(metadata):
 d,ec,m,_=metadata;r=P.check_geometry(d,ec,m)
 assert r['ROM_words']==6144182800 and r['ROM_macros']==1500067 and r['HBM_sectors']==432 and r['flat_sector_bits']==33
@pytest.mark.parametrize('field,value,match',[('word_containers',6144182799,'whole ROM'),('physical4096x274_macros',1500066,'whole ROM')])
def test_global_geometry_mutations(metadata,field,value,match):
 d,ec,m,_=metadata;d=copy.deepcopy(d);d['ROM_candidate'][field]=value
 with pytest.raises(ValueError,match=match):P.check_geometry(d,ec,m)
def test_wrong_macro_rounding(metadata):
 d,ec,m,_=metadata;d=copy.deepcopy(d);d['ROM_candidate']['columns'][0]['macros']-=1
 with pytest.raises(ValueError,match='perbank'):P.check_geometry(d,ec,m)
def test_24bit_flat_aperture_not_admitted(metadata):
 d,ec,m,_=metadata;d=copy.deepcopy(d);d['HBM_candidate']['compact_whole_table_flat_sector_address_bits']=24
 with pytest.raises(ValueError,match='aperture'):P.check_geometry(d,ec,m)
def test_sector_reassembly_not_eight_sectors(metadata):
 d,ec,m,_=metadata;d=copy.deepcopy(d);d['HBM_candidate']['sectors_per_token']=384
 with pytest.raises(ValueError,match='transfer'):P.check_geometry(d,ec,m)
def test_L1_not_promoted(metadata):
 d,ec,m,_=metadata;d=copy.deepcopy(d);d['generated_constants']['L1']['source_pair_complete']=True
 with pytest.raises(ValueError,match='L1'):P.check_geometry(d,ec,m)
def test_retained_coefficient_manifest_and_exact_product(metadata):
 d,*_=metadata;r,reads=P.retained_L14(d)
 assert r['finite_coefficients']==20480 and r['nonfinite_coefficients']==0 and sum(x['bytes'] for x in reads)==81920
 assert r['FP32_product_bits_sha256']=='ab43ae81a7cc77c56b063a7ba730f5f1535c76d04d1dd8507cb6ad3bca22e9fe'
def test_no_physical_credit(metadata):
 d,ec,m,_=metadata;d=copy.deepcopy(d);d['ROM_candidate']['qualification']=True
 with pytest.raises(ValueError,match='admission'):P.check_geometry(d,ec,m)
