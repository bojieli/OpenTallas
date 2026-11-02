import copy
import numpy as np
import ft_sites_unblock as F
from vector_ft_move import move,points_at


def test_polyline_candidates_match_scalar_exactly_at_corners():
    route=[(10.,100.),(250.,100.),(250.,400.),(700.,400.)]
    positions=np.r_[np.linspace(0,F.C.plen(route),1000),0,240,540,F.C.plen(route)]
    np.testing.assert_array_equal(points_at(route,positions),np.array([F.C.point_at(route,t) for t in positions]))


def test_move_and_free_fallback_preserve_scalar_candidate_ties():
    grow=[(150,60,350,180)]
    free=np.mgrid[10:800:2.16,10:500:2.16].reshape(2,-1).T
    free=free[~((free[:,0]>150)&(free[:,0]<350)&(free[:,1]>60)&(free[:,1]<180))]
    pts={}
    for bit in range(4):
        a=(10.,100.+bit);z=(700.,400.+bit);route=F.C.zroute(a,z,'W','E');length=F.C.plen(route)
        pts[bit]=(a,z,route,length,[F.C.point_at(route,length*j/4) for j in range(1,4)])
    a,b=copy.deepcopy(pts),copy.deepcopy(pts);old=F.FRAME[:]
    try:
        F.FRAME[:]=[800,500]
        assert F._move(a,list(a),4,grow,free,385,'test','ft')==move(b,list(b),4,grow,free,385,'test','ft')
        assert a==b
    finally:F.FRAME[:]=old
