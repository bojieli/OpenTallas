from types import SimpleNamespace
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import Report, check_station_sites

def test_station_guard_counts_internal_and_per_bit_points():
    t = dict(hard_cores=[dict(inst="macro", origin_um=[10,10], outline_um=[20,20], track_offset_um=[1,0])],
             internal_stations=[dict(conn="a|b", regs_um=[[5,5],[12,12]])],
             ft_slots=[dict(name="ft0", regs_um=[[31,20]],
                           bit_sites_um=[[[15,15],[40,40]],[[11,20]]])])
    r=Report();out=check_station_sites(SimpleNamespace(types={"tile":t}),r)
    assert out["violations"] == 2
    assert out["points"] == 6
    assert out["types"] == ["tile"]
    assert len(r.errors()) == 2

def test_channel_sites_are_legal_and_core_offset_is_respected():
    t = dict(hard_cores=[dict(inst="macro", origin_um=[10,10], outline_um=[20,20], track_offset_um=[1,0])],
             internal_stations=[dict(conn="a|b", regs_um=[[10.5,20],[31,20],[11,10],[5,5]])])
    r=Report();out=check_station_sites(SimpleNamespace(types={"tile":t}),r)
    assert out["violations"] == 0
    assert not r.errors()
