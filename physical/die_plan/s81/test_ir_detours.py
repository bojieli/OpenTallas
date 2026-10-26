"""A far-link lane must leave the PHY row and use legal FT partitions."""
import ast
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import pytest


def router():
    tree=ast.parse((Path(__file__).parent/'gen_plan_v4.py').read_text())
    wanted={'seg_path','poly_cells','candidates','ir_candidates','route'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in wanted]
    ns={'NC':3,'NR':2,'XCOST':dict(serdes=.6,frame=.6,unit=.4)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'routing-mechanism','exec'),ns)
    return ns['route']

class Grid:
    def __init__(self, frame_ft=True):
        self.owner={(0,0):'lk_src',(1,0):'lk_other',(2,0):'dst',
                    (0,1):'f0',(1,1):'f1',(2,1):'f2'}
        self.P={}
        for cell,name in self.owner.items():
            kind='serdes'if name.startswith('lk_')else'frame'if name.startswith('f')else'unit'
            self.P[name]=SimpleNamespace(kind=kind,ft_ok=frame_ft if kind=='frame'else True,
                                         cells=lambda cell=cell:[cell])
        self.load=defaultdict(int)
    def fkey(self,a,b):return tuple(sorted((a,b)))
    def cap(self,a,b):return 10000

def test_phy_transit_detour_and_missing_channel_negative():
    route=router()
    def lane():return [{'id':'far_coll','src':('lk_src','o'),'dst':('dst','i'),'width':512}]
    legacy=route(Grid(),lane(),{})['far_coll']
    assert (1,0)in legacy
    corrected=route(Grid(),lane(),{},ir_detours=True)['far_coll']
    assert (1,0)not in corrected
    assert corrected==[(0,0),(0,1),(1,1),(2,1),(2,0)]
    with pytest.raises(SystemExit,match='no route for far_coll'):
        route(Grid(frame_ft=False),lane(),{},ir_detours=True)
