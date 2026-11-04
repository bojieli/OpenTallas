import numpy as np
import pytest
from cached_ft_reach import CachedReach, l1_distance


def test_l1_matches_bruteforce_including_empty_goal():
    rng=np.random.default_rng(17)
    for shape in [(1,11),(3,11),(19,11)]:
        for mask in [rng.random(shape)<.1,np.zeros(shape,dtype=bool)]:
            points=np.argwhere(mask)
            expected=(np.min(np.abs(np.indices(shape).transpose(1,2,0)[:,:,None,:]-points).sum(-1)*2.16,axis=2)
                      if len(points) else np.full(shape,1e9))
            np.testing.assert_allclose(l1_distance(mask,2.16),expected,atol=1e-7)


def fixture():
    solver=CachedReach([1000,600],[(400,0,600,300)])
    solver.set_goals({0:(980,200),1:(980,204)})
    args=((20,200),(980,200),[(250,200),(500,320),(750,200)],4,390,0)
    return solver,args


def test_cached_and_uncached_keep_exact_outputs_and_stage_count():
    solver,args=fixture()
    a=solver.solve(*args,use_cache=False)
    assert a==solver.solve(*args)==solver.solve(*args)
    assert len(a)==3 and solver.hits==1
    for goal in [(980,200),(980,204)]:
        assert abs(a[-1][0]-goal[0])+abs(a[-1][1]-goal[1])<=388.5


def test_goal_budget_and_stage_are_distinct_cache_keys():
    solver,args=fixture();solver.solve(*args)
    solver.solve(*args[:-2],380,args[-1])
    solver.set_goals({0:(980,210)})
    changed=(args[0],(980,210),args[2],args[3],args[4],args[5])
    solver.solve(*changed)
    assert solver.misses==3 and solver.hits==0


def test_rejects_stale_geometry_and_outside_goal():
    solver,args=fixture()
    with pytest.raises(ValueError,match='outside immutable goal'):
        solver.solve(args[0],(980,250),*args[2:])
    with pytest.raises(ValueError,match='stale reach geometry'):
        solver(args[0],args[1],args[2],4,[(401,0,600,300)],390,'root','lane',0)
