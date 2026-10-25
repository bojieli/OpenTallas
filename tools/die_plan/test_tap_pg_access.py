"""Interior reset/clock pins must leave access to the lower layer without touching partition PG."""
import copy
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import gen_phys as G
import schema as S


def P():
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text());return S.Plan(raw)


def clear(P,xy):
    top=P.layer_budget['partition_signal_max'];L=P.layers[top];low=f'M{int(top[1:])-1}'
    for ln,c in ((top,xy[0] if L['dir']=='V' else xy[1]),(low,xy[1] if L['dir']=='V' else xy[0])):
        assert all(not S.pg_blocked(ln,c-o) for o in (0,G.CORE_MARGIN_UM))
        lay=P.layers[ln]
        assert abs((c-lay['offset_um'])/lay['pitch_um']-round((c-lay['offset_um'])/lay['pitch_um']))<1e-6


def test_t30_reset_pin_and_lower_access_move_to_free_tracks():
    p=P()
    for xy in ((8.608,153.376),(1434.272,766.816),(4.32,2.16),(0,0)):
        got=G._snap_tap(p,*xy)
        clear(p,got)
        assert abs(got[0]-xy[0])+abs(got[1]-xy[1])<1.2
        assert G._snap_tap(p,*got)==got


def test_hard_macro_interface_is_not_moved_for_pg():
    p=P();xy=(1434.272,766.816)
    assert G._snap_tap(p,*xy,pg_legal=False)==xy


def test_soft_clock_and_wavefront_reset_share_safe_coordinates():
    import reset_tree as RT
    p=P();p.reset['release']='wavefront'
    for tn in p.types:
        for _,x,y in G.tap_pins(p,tn)+G.reset_out_pins(p,tn):clear(p,(x,y))
        T=RT.for_type(p,tn)
        assert RT.verify(T)==[] and T['max_hop_um']<=405
