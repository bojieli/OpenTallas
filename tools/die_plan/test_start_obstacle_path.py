import pytest
from start_obstacle_path import path,relay_sites,length


def test_pv_west_macro_detour():
    boxes=[[9.024,43.2,389.184,233.28],[9.024,336.96,389.184,527.04]]
    p=path((21.6,12),(400,500),boxes,bounds=(4.32,4.32,2160,1300))
    s=relay_sites(p)
    assert all(not (a-4.32<x<c+4.32 and b-4.32<y<d+4.32) for x,y in s for a,b,c,d in boxes)
    assert length(p)/(len(s)+1)<=340
    assert len(s)>0


def test_endpoint_in_macro_fails_instead_of_moving_contract():
    with pytest.raises(ValueError,match='endpoint'):
        path((0,0),(21.6,151),[[9.024,43.2,389.184,233.28]])


def test_shared_depth_and_insufficient_depth():
    p=path((0,0),(1000,0),[])
    assert len(relay_sites(p,5))==5
    with pytest.raises(ValueError,match='depth'): relay_sites(p,1)


def test_wall_has_no_legal_corridor():
    with pytest.raises(ValueError,match='corridor'):
        path((5,50),(95,50),[[40,-10,60,110]],bounds=(0,0,100,100))


def test_negative_control_straight_line_enters_macro():
    box=[10,40,390,234]
    legacy=relay_sites([(20,12),(20,500)],2)
    assert any(box[0]<x<box[2] and box[1]<y<box[3] for x,y in legacy)
    new=relay_sites(path((20,12),(400,500),[box]))
    assert all(not (box[0]<x<box[2] and box[1]<y<box[3]) for x,y in new)


def test_storage_band_excludes_cells_but_allows_wire():
    points=[(0,0),(1000,0)]
    sites=relay_sites(points,3,max_hop_um=405,site_boxes=[[210,-20,290,20]])
    assert all(not 205.68<x<294.32 for x,y in sites)
    chain=[[0,0]]+sites+[[1000,0]]
    assert max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(chain,chain[1:]))<=405


def test_storage_wall_longer_than_hop_fails():
    with pytest.raises(ValueError,match='legal relay'):
        relay_sites([(0,0),(1500,0)],4,max_hop_um=405,site_boxes=[[250,-20,1000,20]])
