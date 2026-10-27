import itertools
import pytest
import hub_repack as HR
from hub_shelf_dp import pack_hub_dp


def test_six_shelves_close_geometry_historical_heuristic_misses():
    cores=[dict(inst=f'c{i}',w=216.0,h=43.2,ocx=112.32,ocy=25+47.52*i) for i in range(6)]
    with pytest.raises(ValueError):HR.pack_hub(224.64,289.44,cores,lanes=(4.32,),shelves=(2,3,4,5,1))
    p,info=pack_hub_dp(224.64,289.44,cores,lanes=(4.32,))
    assert len(p)==6 and info['shelves']==6
    rects=[]
    for c in cores:
        x,y=p[c['inst']];assert x>=0 and y>=0 and x+c['w']<=224.64+1e-6 and y+c['h']<=289.44+1e-6
        rects.append((x,y,x+c['w'],y+c['h']))
    for a,b in itertools.combinations(rects,2):assert a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]
    with pytest.raises(ValueError):pack_hub_dp(224.64,280,cores,lanes=(4.32,))


def test_never_silently_replaces_connection_score():
    with pytest.raises(ValueError,match='connection-scored'):
        pack_hub_dp(100,100,[dict(inst='c',w=20,h=20,ocx=30,ocy=30)],conns=[(('c',0,0),(None,0,0),0)])
