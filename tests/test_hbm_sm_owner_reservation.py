import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hbm_sm_owner_reservation as O


def test_all_native_owner_bays_are_priced_and_clear():
    r,p=O.generate()
    assert len(r['bays'])==32
    assert not r['bay_macro_collisions']
    assert r['legality']['overlaps']==r['legality']['outside']==0
    assert r['grid_reserved_owner_um']==[256.176,129.6]
    assert r['total_owner_reservation_um2']==32*256.176*129.6
    assert r['additional_existing_network_instances']==4
    assert r['selected'] is False
    assert len(p['result_pin_bays'])==32


def test_descriptor_bays_fit_without_using_result_or_owner_space():
    r,p=O.generate(True)
    assert len(r['descriptor_bays'])==32
    assert r['descriptor_pin_manhattan_upper_um']<100
    assert r['total_descriptor_reservation_um2']==32*128.304*64.8
    boxes=p['result_pin_bays']+p['native_owner_bays']+p['native_descriptor_bays']
    for k,a in enumerate(boxes):
        x0,y0,x1,y1=a['box_um']
        for b in boxes[k+1:]:
            u0,v0,u1,v1=b['box_um']
            assert not(min(x1,u1)>max(x0,u0)+1e-6 and min(y1,v1)>max(y0,v0)+1e-6)
