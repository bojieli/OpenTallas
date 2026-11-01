from types import SimpleNamespace
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import vms_minmove_plan as P

def cell(x,y,name='q'):
 return ('S','DFF',x-.2,y-.135,x+.2,y+.135,name)

def test_full_neighbour_graph_keeps_every_launch_not_only_worst():
 cells={0:cell(0,0),1:cell(10,0),2:cell(5,5),3:('L','AND',1,1,2,2,'gate')}
 nets=[('SIGNAL',('i',0,False),[('i',3,False)]),('SIGNAL',('i',1,False),[('i',3,False)]),('SIGNAL',('i',3,False),[('i',2,False)]),('CLOCK',('i',2,False),[('i',0,True)])]
 D=SimpleNamespace(cells=cells,nets=nets,drives=defaultdict(list,{0:[0],1:[1],3:[2],2:[3]}),kind=lambda i:cells[i][0])
 edges,adj=P.neighbours(D)
 assert edges==[(0,2),(1,2)] and adj[2]=={0,1}

def test_nearest_site_respects_every_neighbour_and_macro_clearance():
 cells={0:cell(15,15),1:cell(2,2),2:cell(28,28),3:('M','SRAM',10,10,20,20,'macro')}
 D=SimpleNamespace(cells=cells,extra={'core':(0,0,30,30)})
 p=P.nearest(D,0,{0:{1,2}},28,{})
 assert p is not None
 assert max(abs(p[0]-x)+abs(p[1]-y) for x,y in [(2,2),(28,28)])<=28+1e-9
 assert not (10-2.16-.702<p[0]<20+2.16+.702 and 10-2.16-.135<p[1]<20+2.16+.135)
 assert P.nearest(D,0,{0:{1,2}},20,{}) is None
