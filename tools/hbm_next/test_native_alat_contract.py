"""Explicit ALAT metadata preserves old positional NativeTiming contracts."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_layer_vehicle.native_profile import NativeTiming
from hbm_static import su_lane_build as B


def test_default_profile_fields_stay_unchanged():
    old=NativeTiming(18,15,None,14,5,1)
    assert old.lane_alat==3 and 'alat' not in old.as_dict()
    candidate=NativeTiming(18,15,None,14,5,1,4)
    assert candidate.as_dict()==dict(old.as_dict(),alat=4)
    assert candidate.fill_commit==old.fill_commit and candidate.drain_done==old.drain_done
    assert B.lin(candidate.lane_mlat,candidate.lane_alat,1)-B.lin(old.lane_mlat,old.lane_alat,1)==1
    assert B.side_ii(6,5,4)-B.side_ii(6,5,3)==18
    assert candidate!=old  # source-qualified fixed-3 lowerers continue refusing a different profile


@pytest.mark.parametrize('bad', [0,2,5,'4'])
def test_invalid_adder_profile_refused(bad):
    with pytest.raises(ValueError,match='ALAT'):
        NativeTiming(18,15,alat=bad)
