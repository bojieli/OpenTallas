"""Optional physical-planner observations must never alter existing reach verdicts."""
from types import SimpleNamespace
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import geom_rules as G

def design(distance):
 c={1:('S','DFF',0,0,1,1,'launch'),2:('S','DFF',distance,0,distance+1,1,'capture')}
 return SimpleNamespace(cells=c,drives={1:[0]},nets=[('SIGNAL',('i',1,False),[('i',2,False)])],kind=lambda i:c[i][0])

def test_observer_margin_does_not_change_gate_or_output():
 d=design(385);before=G.r2r_metrics(d);pairs=[]
 assert G.r2r_metrics(d,capture_pairs=pairs,collect_above=380)==before
 assert before['r2r_max']==385 and before['r2r_captures_gt405']==0
 assert pairs==[dict(distance_um=385,launch='launch',capture='capture',launch_xy=[.5,.5],capture_xy=[385.5,.5])]

def test_default_observer_only_collects_actual_failing_pairs():
 pairs=[];m=G.r2r_metrics(design(420),capture_pairs=pairs)
 assert m['r2r_captures_gt405']==1 and pairs[0]['distance_um']==420
 pairs=[];m=G.r2r_metrics(design(405),capture_pairs=pairs)
 assert m['r2r_captures_gt405']==0 and pairs==[]
