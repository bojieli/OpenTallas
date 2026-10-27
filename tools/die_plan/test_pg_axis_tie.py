from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import die_clock_mesh as C
import pytest

def fixture():
    xs=[181.44+345.6*i for i in range(32)]
    shapes=[('VSS','M9',x-.24,0.,x+.24,27043.2) for x in xs]
    return xs,shapes

def test_half_track_phase_survives_integer_period_translations():
    xs,sh=fixture()
    snapped=C.pg_free_axis(xs,sh,'M9',0,11076.48,{'pitch_um':.08,'offset_um':.04},.32,.08,2.,tie_break='positive')
    assert [round(x-y,6) for x,y in zip(snapped,xs)]==[.68]*32
    assert max(abs((b-a)-345.6) for a,b in zip(snapped,snapped[1:]))<1e-8

def test_unknown_policy_is_not_silently_a_legacy_route():
    xs,sh=fixture()
    with pytest.raises(ValueError,match='tie policy'):
        C.pg_free_axis(xs,sh,'M9',0,11076.48,{'pitch_um':.08,'offset_um':.04},.32,.08,2.,tie_break='anything')

def test_outward_policy_preserves_die_mirror_symmetry():
    xs,sh=fixture()
    W=11076.48
    snapped=C.pg_free_axis(xs,sh,'M9',0,W,{'pitch_um':.08,'offset_um':.04},.32,.08,2.,tie_break='outward')
    assert [round(x-y,6) for x,y in zip(snapped,xs)]==[-.68]*16+[.68]*16
    assert all(abs(a+b-W)<1e-8 for a,b in zip(snapped,reversed(snapped)))
