"""Compacting reservations must preserve real gaps and the allocator's first free site."""
import pytest
from test_landing_status_slide_resize import _run

@pytest.mark.parametrize('ranges', [
    [(0,108),(108,270),(162,324),(54,108)],
    [(54,108),(162,324),(108,270),(0,108)],
    [(162,324),(0,108),(108,270),(108,270)],
])
def test_touching_nested_reservations_have_same_first_free_site(ranges):
    setup='set cland_occ {}\n'+''.join(f'cland_occupy {l} 0 {u-l} 270\n'for l,u in ranges)
    assert _run(setup+'cland_put ins {0 0 10 .27} ring:x')==[324,0]

@pytest.mark.parametrize('mode,expected', [(None,[270,0]),('1',[810,0])])
def test_positive_gap_remains_usable_at_the_unchanged_fit_footprint(mode,expected):
    setup='set cland_occ {}\ncland_occupy 0 0 270 270\ncland_occupy 540 0 270 270\n'
    env={}if mode is None else{'OT_CLAND_FIT_RESERVE':mode}
    assert _run(setup+'cland_put ins {0 0 10 .27} ring:x',env)==expected


def test_multirow_reservation_blocks_both_rows():
    setup='set cland_occ {}\ncland_occupy 0 0 270 540\n'
    assert _run(setup+'cland_put ins {0 .27 10 .54} ring:x')==[270,270]
