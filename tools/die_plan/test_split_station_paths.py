import math
from pathlib import Path
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from split_station_paths import CELL_UM, PITCH_UM, StationPathError, _Router, plan_slot


def _assert_slots(result,outline,cores,start,end):
    router=_Router(outline,cores,4.32)
    assert len(result["bit_sites_um"])==result["stations"]-1
    occupied=set()
    previous=start
    for bank in result["bit_sites_um"]:
        assert len(bank)==len(start)
        for before,site in zip(previous,bank):
            assert router.length(tuple(before),tuple(site))<=405+1e-6
            assert tuple(site) not in occupied
            occupied.add(tuple(site))
            for bx,by,c,d in router.boxes:
                x,y=site;w,h=CELL_UM
                assert not (min(x+w,c)-max(x,bx)>1e-6 and min(y+h,d)-max(y,by)>1e-6)
        previous=bank
    for p,q in zip(previous,end):assert router.length(tuple(p),tuple(q))<=405+1e-6


def test_wide_bus_has_distinct_stage_cells_and_real_bit_reach():
    start=[[1.404,100+i*.54]for i in range(24)]
    end=[[914.436,150+i*.54]for i in range(24)]
    r=plan_slot([915.84,500],[],start,end)
    _assert_slots(r,[915.84,500],[],start,end)
    assert r["stations"]>=4


def test_macro_wall_is_routed_through_the_free_street():
    cores=[dict(inst="bank",origin_um=[25.92,43.2],outline_um=[380.16,190.08]),
           dict(inst="bank2",origin_um=[509.76,43.2],outline_um=[380.16,190.08])]
    start=[[1.404,132+i*.54]for i in range(24)]
    end=[[914.436,45+i*.54]for i in range(24)]
    r=plan_slot([915.84,500],cores,start,end)
    _assert_slots(r,[915.84,500],cores,start,end)
    assert r["station_path_report"]["max_path_um"]>915


def test_shared_occupancy_keeps_two_banks_disjoint():
    start=[[1.404,100+i*.54]for i in range(8)]
    end=[[914.436,150+i*.54]for i in range(8)]
    occupied=set()
    a=plan_slot([915.84,500],[],start,end,occupied=occupied)
    b=plan_slot([915.84,500],[],start,end,occupied=occupied)
    sa={tuple(x) for bank in a["bit_sites_um"]for x in bank}
    sb={tuple(x) for bank in b["bit_sites_um"]for x in bank}
    assert not sa&sb


def test_blocked_path_fails_without_consuming_occupancy():
    occupied={(0,0)}
    with pytest.raises(StationPathError):
        plan_slot([915.84,500],[dict(inst="wall",origin_um=[400,0],outline_um=[100,500])],
                  [[1.404,100]],[[914.436,150]],occupied=occupied)
    assert occupied=={(0,0)}


def test_grid_cannot_be_smaller_than_real_cell_envelope():
    with pytest.raises(StationPathError,match="packing grid"):
        plan_slot([500,500],[],[[0,10]],[[500,10]],pitch_um=[.1,.1])


def test_inherited_arbitrary_grid_cells_remain_unoccupied():
    blocks=[(280.123,95.456,80,35)]
    r=plan_slot([915.84,500],[],[[1.404,100+i*.54]for i in range(8)],
                [[914.436,150+i*.54]for i in range(8)],occupied_rects=blocks)
    for bank in r["bit_sites_um"]:
        for x,y in bank:
            for bx,by,w,h in blocks:
                assert not (min(x+CELL_UM[0],bx+w)-max(x,bx)>1e-6 and
                            min(y+CELL_UM[1],by+h)-max(y,by)>1e-6)
