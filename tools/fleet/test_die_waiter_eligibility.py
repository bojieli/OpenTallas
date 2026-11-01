from importlib.machinery import SourceFileLoader
from pathlib import Path
import pytest
M=SourceFileLoader('die_waiter_reconcile',str(Path(__file__).with_name('ot-heavy-reconcile'))).load_module()

@pytest.mark.parametrize('env,load,ncpu,factor,blocked',[
 ({},179,112,1.5,True), ({},168,112,1.5,True), ({},167.99,112,1.5,False),
 ({'OT_HEAVY_CPU':'crit'},179,112,1.5,False),
 (None,179,112,1.5,False), ({'OT_HEAVY_CPU':'unknown'},179,112,1.5,False),
 ({},179,112,0,False), ({},None,112,1.5,False), ({},179,None,1.5,False),
 ({},179,112,None,False), ({},float('nan'),112,1.5,False),
 ({'OMP_NUM_THREADS':'2'},179,112,1.5,False),
])
def test_only_positively_cpu_blocked_noncritical_waiter_loses_reservation(env,load,ncpu,factor,blocked):
 assert M.die_waiter_cpu_blocked(env,load,ncpu,factor)==blocked
