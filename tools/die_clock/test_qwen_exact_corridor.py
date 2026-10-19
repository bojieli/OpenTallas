import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unittest
from qwen_exact_corridor import ExactBayGrid,ExactForwardedBuilder,check_reach
from qwen_corridor_audit import bay,overlap


def test_full_footprint_overlap_not_origin_only():
    # Free1um strip has legal point origins, but cannot contain a1.62um cell.
    assert bay((0,0),[(1.0,0,10,10)]) is None
    p=bay((0,0),[(0,0,10,6.48)])
    assert p is not None
    assert not overlap((*p,p[0]+1.62,p[1]+.27),(0,0,10,6.48))


def test_reserve_occupied_bays():
    g=ExactBayGrid(30,30,[('rstt_a',(0,0,10,6.48))])
    first=g.reserve((0,0));second=g.reserve((0,0))
    assert not overlap((*first,first[0]+1.62,first[1]+.27),(*second,second[0]+1.62,second[1]+.27))


def test_region_tree_buffers_after_floorplan_are_obstacles():
    before=ExactBayGrid(30,30,[('rstt_a',(0,0,10,6.48))])
    assert before.free((0,0))
    after=ExactBayGrid(30,30,[('rstt_a',(0,0,10,6.48)),('dc_root_new',(0,6.48,10,10))])
    assert not after.free((0,0))


def test_post_placement_reach_mutant_rejected():
    g=ExactBayGrid(500,30,[])
    path=[(x,0) for x in range(40)]
    assert check_reach(path,(5,5),(395,5),g)==390
    try:
        check_reach(path,(-15,5),(395,5),g)
    except ValueError as e:
        assert '>405' in str(e)
    else:
        raise AssertionError('reach mutant escaped')


def test_exact_binary_spine_reserves_and_bounds_every_stage():
    g=ExactBayGrid(1200,100,[])
    b=ExactForwardedBuilder(g,'test')
    leaves=[[('left/A','BUF',100,50,'l')],[('right/A','BUF',1100,50,'r')]]
    r=b.build('gen/Y',(20,50),leaves)
    assert r['max_placed_routed_bound_um']<=405
    assert all(len(loads)<=2 for _,_,loads in b.nets)
    boxes=[(x,y,x+1.62,y+.27) for _,_,x,y in b.bufs]
    assert not any(overlap(a,c) for i,a in enumerate(boxes) for c in boxes[i+1:])


class ExactCorridor(unittest.TestCase):
    def test_full_footprint_overlap_not_origin_only(self): test_full_footprint_overlap_not_origin_only()
    def test_reserve_occupied_bays(self): test_reserve_occupied_bays()
    def test_region_tree_buffers_after_floorplan_are_obstacles(self): test_region_tree_buffers_after_floorplan_are_obstacles()
    def test_post_placement_reach_mutant_rejected(self): test_post_placement_reach_mutant_rejected()
    def test_exact_binary_spine_reserves_and_bounds_every_stage(self): test_exact_binary_spine_reserves_and_bounds_every_stage()

if __name__=='__main__': unittest.main()
