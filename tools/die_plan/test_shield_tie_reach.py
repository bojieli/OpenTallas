import math
import pytest
import die_clock_128 as C

ND=dict(width=.16,space=.08,rf=.25,cf=1.3)
TRACKS={k:dict(pitch_um=.08,offset_um=.04) for k in ['M8','M9']}

def router(**kw):
    r=C.TrackRouter(ND,'VSS',TRACKS,max_move=8.64,**kw)
    r.reserve([('M9','VSS','pg',19.98-.24,19.98+.24,0,100)])
    return r

def test_wide_pg_shield_ground_reach_is_separate_from_clock_track_motion():
    assert router().tie_ext('M8',50,0,.16) is None
    r=router(tie_reach_um=20.02)
    assert 19.8<r.tie_ext('M8',50,0,.16)<20.02
    assert r.max_move==8.64

def test_reference_cannot_reach_ground_beyond_declared_footprint():
    assert router(tie_reach_um=10).tie_ext('M8',50,0,.16) is None

@pytest.mark.parametrize('value',[-1,float('nan'),float('inf')])
def test_invalid_tie_reach_rejected(value):
    with pytest.raises(ValueError):router(tie_reach_um=value)

@pytest.mark.parametrize('extension,valid',[(9.17,True),(9.17,False)])
def test_actual_reserved_span_controls_short_trunk_after_track_rounding(monkeypatch,extension,valid):
    # Actual q6 root witness: final drop snaps24nm inward. The old scalar
    # e<=reserved+max_move proxy rejected a tie exactly inside the reservation.
    class R:
        max_move=8.64
        tie_reach_um=20.02
        def extend_shield_reservation(self,*args):return valid
        def place(self,layer,*args,**kw):
            return (13004.04,C.DRAWN,.506) if layer=='M8' else (5539.08,C.FLANK,None)
        def tie_ext(self,*args):return extension
    monkeypatch.setattr(C,'_centre',lambda cells,name,*args:cells[name]['point'])
    m=dict(meta=dict(root_um=[5538.92,13003.2]),taps=[])
    cells={'load':dict(point=(5538.264,13003.2))}
    nets=[dict(name='root',drv='port:root',loads=['load'])]
    if valid:
        result=C.fixed_wires(m,cells,nets,1.62,.27,off=.84,router=R())
        assert result[0]['shield_ext'][0]==extension
    else:
        with pytest.raises(C.PlanError):C.fixed_wires(m,cells,nets,1.62,.27,off=.84,router=R())


def test_actual_shield_extension_checks_other_net_geometry():
    r=router(tie_reach_um=20.02)
    assert r.extend_shield_reservation('M8',50,0,.16,'clock',9.17)
    intruder=list(C.seg_shapes('M8',50,0,.16,'clock',ND,'VSS',ext=9.17)[1])
    intruder[1]='other_net'
    r.reserve([tuple(intruder)])
    assert not r.extend_shield_reservation('M8',50,0,.16,'clock',9.17)
