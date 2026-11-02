"""An explicit FF fill window cannot enlarge or replace the reserved band."""
import copy
import pytest
import landing_place as L


def band():
    return dict(rect_um=[915.1493, 4.32, 1036.1093, 18.144], ring_place='ff',
                ff_rect_um=[928.8, 4.32, 961.2, 18.144])


def test_measured_contained_window_preserves_outer_band():
    b=band();before=copy.deepcopy(b)
    assert L.band_rects('kv3_hroot','i_slg_Q_N_o_ctl',b,dict(outline_um=[1900.8,838.08])) == [b['ff_rect_um']]
    assert b==before
    b.pop('ff_rect_um')
    assert L.band_rects('kv3_hroot','i_slg_Q_N_o_ctl',b) == [b['rect_um']]


@pytest.mark.parametrize('change', [dict(ring_place='all'),dict(rects_um=[[0,0,1,1],[2,2,3,3]]),
    dict(ff_rect_um=[914,4.32,961.2,18.144]),dict(ff_rect_um=[928.8,4.32,1037,18.144]),
    dict(ff_rect_um=[928.8,4.32,928.8,18.144]),dict(ff_rect_um=[928.8,False,961.2,18.144]),
    dict(ff_rect_um=[928.8,4.32,float('nan'),18.144])])
def test_invalid_window_fails_closed(change):
    b=band();b.update(change)
    with pytest.raises(ValueError):L.band_rects('kv3_hroot','i_slg_Q_N_o_ctl',b)
