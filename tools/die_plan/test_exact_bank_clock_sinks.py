import types
import gen_phys
import taps


def test_exact_payload_epoch_banks_are_clock_sinks_at_actual_locations(monkeypatch):
    e=dict(conn="bus:o",bit_site_cell_um=[1.4,.27],
           bit_sites_um=[[[10,10],[12,10],[14,10]],[[20,20],[22,20],[24,20]]],
           face_bit_sites_um=[[30,30],[32,30],[34,30]])
    t=dict(outline_um=[100,100],buses=[dict(name="o",dir="out")],internal_stations=[e])
    p=types.SimpleNamespace(types={"t":t})
    monkeypatch.setattr(gen_phys,"type_pins",lambda p,tn:[("o",0,"M5",50,0,"S"),("o",1,"M5",52,0,"S")])
    points=taps.planned_sinks(p,"t")
    assert len(points)==9
    assert points[:3]==[(30.7,30.135,"face"),(32.7,30.135,"face"),(34.7,30.135,"face_epoch")]
    assert [q for q in points if q[2]=="ist"]==[(10.7,10.135,"ist"),(12.7,10.135,"ist"),
        (14.7,10.135,"ist"),(20.7,20.135,"ist"),(22.7,20.135,"ist"),(24.7,20.135,"ist")]


def test_default_station_census_is_unchanged():
    t=dict(internal_stations=[dict(conn="bus:o",regs_um=[[10,10]])])
    assert taps.per_bit_station_sites(t,[])==[]
