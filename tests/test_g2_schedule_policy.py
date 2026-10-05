"""Residency selection at measured capacity cliffs and unsupported reuse cases."""
import pytest
from tools.g2_schedule_policy import choose_schedule

@pytest.mark.parametrize('rows,cols,depth,first,width', [
    (6,53,80,False,3), (6,53,144,False,3), (6,53,160,True,3),
    (6,53,341,True,3), (6,53,342,True,2), (6,53,512,True,2),
    (6,53,513,True,1), (6,53,1024,True,1), (6,53,1025,False,3),
    (1,53,342,False,3), (6,8,1024,False,3), (6,9,1024,True,1),
])
def test_capacity_choices(rows, cols, depth, first, width):
    selected = choose_schedule(rows, cols, depth)
    assert (selected['pass_first'], selected['pass_columns']) == (first,width)
    if first:
        assert selected['packed_pass_words'] <= 1024
        assert selected['packed_row_words'] > 1024
        assert width == 3 or (width+1)*depth > 1024

@pytest.mark.parametrize('shape', [(0,8,1),(1,0,1),(1,8,0)])
def test_bad_shape(shape):
    with pytest.raises(ValueError):
        choose_schedule(*shape)
