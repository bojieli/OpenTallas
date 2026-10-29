"""Native local clock load isolation preserves the selected buffer and input plan."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import local_entry as L


def test_selected_buffer_and_immutable_source(monkeypatch):
    class Plan:
        die={'outline_um':[100,100]}
    class Site:
        def legal(self,q):return True
    monkeypatch.setattr(L.D,'SiteMap',lambda _:Site())
    ph={'cells':{}}
    stages={'stages':[dict(id='s0',clock_port='sc0',node_cell='b0',flops=7)]}
    sizes={'INV':(1.62,.27),'BUFx8_ASAP7_75t_R':(.864,.27),'BUF4':(.54,.27),'TALL':(.54,.54)}
    v='  INV b0 (.A(root), .Y(n0));'
    t='place_inst -name b0 -location {10.8 10.26} -status FIRM'
    default=L.add(ph,stages,Plan(),v,t,sizes)
    selected=L.add(ph,stages,Plan(),v,t,sizes,master='BUF4')
    assert default['stage_clock_drivers']['sc0']['cell']==L.MASTER
    d=selected['stage_clock_drivers']['sc0']
    assert d['cell']=='BUF4' and d['flop_loads']==7 and d['logical_cycles_added']==0
    assert ph=={'cells':{}}
    with pytest.raises(ValueError,match='already present'):
        L.add(default,stages,Plan(),v,t,sizes)
    with pytest.raises(ValueError,match='single-row'):
        L.add(ph,stages,Plan(),v,t,sizes,master='TALL')


def test_duplicate_clock_port_fails_closed(monkeypatch):
    """DIE-HEAD-29: a second stage on the same clock_port must not overwrite the first driver."""
    class Plan:
        die={'outline_um':[100,100]}
    class Site:
        def legal(self,q):return True
    monkeypatch.setattr(L.D,'SiteMap',lambda _:Site())
    stages={'stages':[dict(id='s0',clock_port='sc0',node_cell='b0',flops=7),dict(id='s1',clock_port='sc0',node_cell='b0',flops=3)]}
    sizes={'INV':(1.62,.27),'BUFx8_ASAP7_75t_R':(.864,.27)}
    v='  INV b0 (.A(root), .Y(n0));'
    t='place_inst -name b0 -location {10.8 10.26} -status FIRM'
    with pytest.raises(ValueError,match='duplicate local clock port sc0'):
        L.add({'cells':{}},stages,Plan(),v,t,sizes)
