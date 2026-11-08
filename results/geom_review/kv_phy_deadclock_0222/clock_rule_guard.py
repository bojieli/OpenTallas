from pathlib import Path
import sys,re
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
sys.path.insert(0,str(Path(__file__).parent))
from bind import Graph,Rules
from event import RULE
def check(rule):
    cells=[];clock_nets=[];payload_nets=[];net=1
    for quadrant in ('EN','ES','WN','WS'):
        for index in range(8):
            ports={};directions={}
            for pin in [f'{prefix}{k}'for prefix in ('fh','rh','pi')for k in range(4)]:
                width=4 if pin[:2] in ('fh','rh')else 289
                ports[pin]=list(range(net,net+width));net+=width
                directions[pin]='output'
                (payload_nets if pin.startswith('pi')else clock_nets).extend(ports[pin])
            cells.append(SimpleNamespace(module='qkd_hbm3e_phy_pc4',path=f'phy_{quadrant}.u_sub.u_s{index}',ports=ports,dirs=directions,kind='leaf'))
    f=SimpleNamespace(cells=cells,top_ports={},const_drivers={})
    errors=[];g=Graph(f,Rules({'clocks':[rule]}),errors)
    assert not errors,errors
    assert all(g.source(n)==('clock','core')for n in clock_nets)
    assert all(g.source(n)[0]=='pin' for n in payload_nets),'LIVE_PAYLOAD_RECLASSIFIED'
    return len(clock_nets),len(payload_nets)
print('CLOCK_RULE_PASS forwarded,payload=',check(RULE))
bad=dict(RULE,pin=RULE['pin'].replace('fh|rh','fh|rh|pi'))
try:check(bad)
except AssertionError as e:
    assert str(e)=='LIVE_PAYLOAD_RECLASSIFIED'
    print('LIVE_PI_CLOCK_MUTANT_CAUGHT')
else:raise AssertionError('live PI mutation survived')
