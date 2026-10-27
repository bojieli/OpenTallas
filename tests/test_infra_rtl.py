"""Explicit infrastructure interfaces never synthesize implicit root ties or active dead ends."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/die_plan'))
import infra_rtl as I

def fixture():
 t=dict(outline_um=[16,16],infra_ports=[dict(name='hci_i',dir='in',kind='clock',leaf='u_core.hci_i',xy_um=[.032,.032],layer='M7'),dict(name='hci_o',dir='out',kind='clock',leaf='u_core.hci_o',xy_um=[8.032,.032],layer='M7')])
 n=[dict(name='a',kind='clock'),dict(name='b',kind='clock'),dict(name='used_monitor',kind='clock',unused=True,owner_inventory='EXACT-UNUSED-1')]
 c=[dict(module='BUFx24_ASAP7_75t_R',inst='u_real_src',bind={'A':dict(signal='root:clk',dir='in'),'Y':dict(signal='a',dir='out')}),dict(module='BUFx24_ASAP7_75t_R',inst='u_real_sink',bind={'A':dict(signal='b',dir='in'),'Y':dict(signal='used_monitor',dir='out')})]
 b=[dict(part='p',port='hci_i',net='a'),dict(part='p',port='hci_o',net='b')]
 return SimpleNamespace(types={'t':t},parts={'p':{'type':'t'}},raw={'infrastructure':dict(nets=n,instances=c,bindings=b)})

def test_closed_graph():
 p=fixture();w,inst,conn=I.die_lines(p)
 assert len(w)==3 and len(inst)==2 and conn['p']==[('hci_i','infra_a'),('hci_o','infra_b')]
 assert '.A(clk)' in inst[0] and '.Y(infra_a)' in inst[0]

@pytest.mark.parametrize('mutant',range(5))
def test_rejects_open_or_fake_clock_bindings(mutant):
 p=fixture();d=p.raw['infrastructure']
 if mutant==0:d['bindings'].pop()
 if mutant==1:d['bindings'][0]['net']='root:clk'
 if mutant==2:d['instances'].pop(0)
 if mutant==3:d['nets'][-1].pop('owner_inventory')
 if mutant==4:d['instances'].append(copy.deepcopy(d['instances'][0]))
 with pytest.raises(ValueError):I.die_lines(p)


def test_no_implicit_network_and_wrong_pin_kind():
 p=fixture();p.raw={}
 with pytest.raises(ValueError,match='implicit'):I.die_lines(p)
 p=fixture();p.types['t']['infra_ports'][0]['kind']='data'
 with pytest.raises(ValueError,match='clock/reset'):I.type_ports(p.types['t'])


def test_physical_interface_position_guard():
 p=fixture();p.types['t']['infra_ports'][0]['xy_um']=[.04,.032]
 with pytest.raises(ValueError,match='M7 track'):I.type_ports(p.types['t'])


def test_provider_source_ports_are_checked():
 p=fixture()
 assert I.die_lines(p,lambda mod:{'A':('input',''),'Y':('output','')})[2]
 for mutant in ({'A':('input',''),'Z':('output','')},{'A':('output',''),'Y':('output','')}):
  with pytest.raises(ValueError,match='provider'):
   I.die_lines(p,lambda mod:mutant)


def test_actual_clock_entry_override_only(monkeypatch):
 fake=SimpleNamespace(tap_grid=lambda p,t:[('clk',0,0)],core_taps=lambda p,t:[('ctap0',0,0,{})])
 monkeypatch.setitem(sys.modules,'schema',fake)
 p=fixture();p.raw['infrastructure']['clock_tap_bindings']=[dict(part='p',port='ctap0',net='b')]
 assert ('ctap0','infra_b') in I.die_lines(p)[2]['p']
 p.raw['infrastructure']['clock_tap_bindings'][0]['port']='made_up_pin'
 with pytest.raises(ValueError,match='clock-entry'):I.die_lines(p)


def test_real_clock_exporter_non_ansi_header():
 text='module die_ctree(root,t_g0);input root;output t_g0;BUFx24 b(.A(root),.Y(t_g0));endmodule'
 assert I.provider_ports(text,'die_ctree',lambda t,m:{})=={'root':('input',''),'t_g0':('output','')}
 with pytest.raises(ValueError,match='direction missing'):
  I.provider_ports(text.replace('output t_g0;',''),'die_ctree',lambda t,m:{})
