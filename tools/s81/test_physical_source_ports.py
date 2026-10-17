"""The physical abstract must retain both independent forwarded clock paths."""
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


def test_station_noninverted_clock_has_distinct_contact(monkeypatch):
    monkeypatch.setattr(G,'STN_PIN_PITCH2',True)
    ports=dict(fi0=('input',1),di0=('input',538),fo0=('output',1),do0=('output',538),fn0=('output',1))
    master=G.Q.Master('dsfd_stnv_538x1',77.76,17.28,3,'test')
    G._LAY_K[0]=1
    G._faces_r8({},master,SimpleNamespace(kind='stn'),ports)
    G._require_physical_source_ports(master,ports)
    assert master.ports['fn0']!=master.ports['fo0']
    del master.ports['fn0']
    with pytest.raises(ValueError,match='fn0'):G._require_physical_source_ports(master,ports)


def test_split_fifo_keeps_second_clock_and_all_second_payload_bits(monkeypatch):
    monkeypatch.setattr(G,'CFIFO_V2',True)
    ports=dict(xf=('input',1),xd=('input',566),xf2=('input',1),xd2=('input',538),rf=('input',1),rd=('input',73),xa=('output',283),xb=('output',266),x2=('output',536),cc=('output',15),st=('input',2),ri=('output',73),co=('output',1),cr=('input',1),rs=('output',1),ck=('input',1),rst=('input',1))
    master=G.Q.Master('dsfd_cfifo',432,60.48,3,'test')
    G._LAY_K[0]=1
    G._faces_r8({},master,SimpleNamespace(kind='cfifo'),ports)
    G._require_physical_source_ports(master,ports)
    assert master.ports['xf2'][1]==1 and master.ports['xd2'][1]==538
    assert master.ports['xf2']!=master.ports['xf']
    for missing in ('xf2','xd2'):
        saved=master.ports.pop(missing)
        with pytest.raises(ValueError,match=missing):G._require_physical_source_ports(master,ports)
        master.ports[missing]=saved


def test_controller_actual_rtl_status_has_distinct_contacts(monkeypatch):
    import die_port_bind as DPB
    path = G.ROOT / 'rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv'
    md, = DPB.parse_modules(path.read_text(), str(path))
    ports = {name: (spec[0], md.width(name, md.env({}))) for name, spec in md.ports.items()}
    assert ports['st'] == ('output', 2)
    # The PHY contact list is unrelated to the missing controller status port.
    monkeypatch.setattr(G, 'real_lef', lambda _: {'name': 'test_phy', 'pins': {}})
    monkeypatch.setattr(G, 'real_ports_r8', lambda: {'test_phy': {'dfi': []}})
    monkeypatch.setattr(G, '_peer_pos', lambda *args: 0)
    monkeypatch.setattr(G, '_LAY_K', [1])
    master = G.Q.Master('dsfd_ctrl', 8400, 200, 7, 'test actual RTL ports')
    G._faces_r8({}, master, SimpleNamespace(kind='ctrl'), ports)
    G._require_physical_source_ports(master, ports)
    assert master.ports['st'][1:4] == (2, 'N', 'M5')
    assert master.ports['st'] != master.ports['ckh']
    del master.ports['st']
    with pytest.raises(ValueError, match='st'):
        G._require_physical_source_ports(master, ports)
