import pytest
import d2d_link_calendar as L


def test_status_is_derived_from_actual_capture_times_and_old_image_is_unchanged():
    assert L.compute_status_offset([8,3,1,10])==40
    assert L.compute_status_offset([6,3,1,9],38)==38
    txd={'C':[13,3,1,15],'K':[170,4,3,3]}
    w=[10,200,30,1800]
    old,_=L.layer_msgs(0,0,w,8,7,40,213,1)
    with pytest.raises(SystemExit,match='TXD collision'):
        L.compile_cal(old,6,7,0,txd)
    offset=L.compute_status_offset(txd['C']);assert offset==45
    new,_=L.layer_msgs(0,0,w,8,7,offset,213,1)
    _,table,_=L.compile_cal(new,6,7,0,txd)
    assert [m for m in old if m['kind']!=15]==[m for m in new if m['kind']!=15]
    status=next(m for m in table if m['src']=='C' and m['kind']==15)
    assert status['wr']==1+max(m['wr'] for m in table if m['src']=='C' and m['tx_port']==0)


def test_status_does_not_collide_with_the_other_producer():
    assert L.compute_status_offset([13,3,1,13])==49
