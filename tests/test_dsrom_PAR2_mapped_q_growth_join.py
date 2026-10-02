import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_PAR2_mapped_q_growth_join as G
import dsrom_PAR2_complete_selector_wire_join as J

@pytest.fixture(scope='module')
def result():return G.build()

def test_q_BF_selector_once(result):
    m=result[0];old=J.build()
    assert m['area']['mapped_q_growth_charged_once_mm2']==pytest.approx(1686*3310.2432/1e6)
    assert m['area']['BF_complete_frame_growth_charged_once_mm2']==old['area']['BF_complete_frame_growth_charged_once_mm2']
    assert m['selector']['reserved_rectangle_mm2']==old['selector']['reserved_rectangle_mm2']

def test_all_compiled_macros_preserved(result):
    m,f,macro,cfg,bands=result
    assert len(f)==2048 and len(macro)==8192 and len(cfg)==14336
    assert sum(r['source_class']=='q_pair' for r in f)==1686
    assert all(r['bbox_DBU'][3]-r['bbox_DBU'][1]==151200 for r in f if r['source_class']=='q_pair')

def test_clock_and_original_failure_not_adopted(result):
    m=result[0]
    assert m['mapped_clock_G0']['q']['distinct_mapped_output_nets']==1
    assert m['actual_I66_review']['original_wrapper_verdict']=='FAIL'
    assert not m['geometry_G0']['physical_build_admitted']
    assert m['new_q_growth_latency']['physical_route_clock_pipeline_delta'] is None
