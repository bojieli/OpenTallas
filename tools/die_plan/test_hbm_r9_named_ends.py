import copy
import hbm_r9_delta as R

def test_overlapping_prototype_uses_explicit_core_identity():
    t=dict(outline_um=[1000,500],hard_cores=[
        dict(inst="A",module="m",origin_um=[100,100],outline_um=[100,100]),
        dict(inst="A.child",module="m",origin_um=[100,100],outline_um=[100,100])],
        internal_stations=[dict(conn="bus:L",launch="A.child.o",capture="face bus L",bits=10,from_um=[200,150],to_um=[1000,150],regs_um=[])])
    old=R.plan_quadrants(copy.deepcopy(t),2)
    new=R.plan_quadrants(copy.deepcopy(t),2,named_ends=True)
    assert old["stations"][0][1][1]=="A"
    assert new["stations"][0][1][1]=="A.child"
