from collections import defaultdict
from types import SimpleNamespace
import bind_plancells as P

def test_only_plan_driven_literal_bits_leave_residual_tie_audit():
    key=('p.leaf','cfg','leafmod')
    b=SimpleNamespace(F=SimpleNamespace(cells=[SimpleNamespace(path='p.leaf',module='leafmod')]),
        G=SimpleNamespace(kind={0:'leaf'}),members={'p':[0]},rel_of=lambda ci:'leaf',
        sinks={(0,'cfg',0):('tied',0),(0,'cfg',1):('tied',1)},
        counts={'tied':2},tied_by_port=defaultdict(int,{'leafmod.cfg <- literal':2}),
        tied_pins={key:[(0,0,'literal'),(1,1,'literal')]},
        errors=['TIED p.leaf.cfg[0] = 0 (literal)','TIED p.leaf.cfg[1] = 1 (literal)'],findings=[])
    obj=P.PlanCells.__new__(P.PlanCells)
    obj.B=b;obj.ptype=lambda p:'t';obj.leafdrv={'t':{('leaf','cfg',0):('net','real_source')}}
    obj.T={'t':{}};obj.explicit=defaultdict(set);obj.stats=defaultdict(int)
    obj.apply_sinks()
    assert b.sinks[(0,'cfg',0)][0]=='plan'
    assert b.counts['tied']==1 and b.counts['plan_driven']==1
    assert b.tied_pins=={key:[(1,1,'literal')]}
    assert b.tied_by_port['leafmod.cfg <- literal']==1
    assert b.errors==['TIED p.leaf.cfg[1] = 1 (literal)']
    obj.leafdrv['t']={('leaf','cfg',1):('net','other_source')}
    obj.apply_sinks()
    assert b.counts['tied']==0
    assert not b.tied_pins and not b.tied_by_port and not b.errors
