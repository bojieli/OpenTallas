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
