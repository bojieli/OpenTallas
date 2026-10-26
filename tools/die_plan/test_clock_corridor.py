import pytest
from clock_corridor import detour_segments, intersects


def test_boundary_phy_domain_detour_preserves_branch_connectivity():
    segs=[(5,50,40,50,1,'M8'),(40,50,80,50,2,'M8'),(40,50,40,90,2,'M9')]
    domains=[(10,0,30,70)]
    out,m,r=detour_segments(segs,domains,(100,100),clear_um=2)
    assert r['changed_edges']==1 and r['wire_delta_um']==44
    assert m[(40,50)]==(40,50)
    assert not any(intersects(s[:2],s[2:4],(8,-2,32,72)) for s in out)
    assert sum(abs(s[0]-s[2])+abs(s[1]-s[3]) for s in out)==159
    assert {s[4] for s in out}=={1,2}


def test_closed_wall_fails_instead_of_routing_through_pg():
    with pytest.raises(ValueError,match='no clock corridor'):
        detour_segments([(5,50,90,50,1,'M8')],[(40,0,60,100)],(100,100),2)


def test_shared_endpoint_moves_consistently():
    out,m,r=detour_segments([(0,20,20,20,1,'M8'),(20,20,80,20,2,'M8')],
                           [(10,0,30,30)],(100,100),2)
    assert r['moved_endpoints']==1
    moved=m[(20,20)]
    assert any(tuple(s[2:4])==moved for s in out if s[4]==1)
    assert any(tuple(s[:2])==moved for s in out if s[4]==2)
