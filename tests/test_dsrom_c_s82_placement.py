import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).resolve().parents[1]/'tools/dsrom_c_s82_placement.py'
s=importlib.util.spec_from_file_location('s82',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture(scope='module')
def d():return m.build()
def test_exact_inventory(d):assert (d['q'],d['BF'],d['weight_macros'],d['cfg_macros'])==(1876,512,9552,16716)
def test_site_conservation(d):assert sorted(a['site'] for a in d['rectangles'] if 'site' in a)==list(range(2388))
def test_known_shapes(d):assert not d['collisions'];assert not d['out_of_die'];assert not d['region_overflow']
def test_return_retained(d):assert d['return_mm2']==pytest.approx(52.89758742528);assert d['return_bits']==69771008
def test_no_credit_or_admission(d):assert d['complement_credit_mm2']==0;assert not d['PnR_admitted'];assert not d['rate_adopted'];assert d['latency']['full_single_user_MTP_delta_us'] is None
def test_capture_full_shape(d):assert d['capture_seats']==576;assert len([a for a in d['rectangles'] if a['kind']=='clock_reservation'])==1
def test_stage_map_regions(d):
 b=m.read('stage_map')['region_bounds'];assert len(b)==129;assert b[-1]==2388;assert set(b[i+1]-b[i] for i in range(128))=={18,19}
