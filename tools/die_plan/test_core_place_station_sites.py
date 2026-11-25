"""SITE-IN-MACRO 11-25: core_place keeps the explicit bit sites of an internal station (write_type re-sites only regs_um) as fixed
points no core may cover, also with --ft-resite (KV A5t6: 22 i_ectl_Q_N_kf bit sites of 8 kv3_pc_v1 types on u_kvpc1_f)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_place as CP  # noqa: E402


def fixed_points(ft_resite):
    t = dict(outline_um=[500.0, 500.0], hard_cores=[],
             ft_slots=[dict(regs_um=[[10.0, 10.0]], bit_sites_um=[[[11.0, 11.0]]])],
             internal_stations=[dict(conn="bus:i_ectl", regs_um=[[100.0, 100.0]],
                                     bit_sites_um=[[[300.0, 300.0], [310.0, 300.0]]], face_bit_sites_um=[[320.0, 300.0]])])
    me = SimpleNamespace(t=t, cfg=dict(ft_resite=ft_resite), W=500.0, H=500.0, owner=lambda p, tol=0.0: None)
    CP.TypeModel._fixed_geometry(me)
    return [tuple(p) for p in me.FP], list(me.FPH)


def test_station_bit_sites_are_fixed_points():
    fp, fph = fixed_points(False)
    for p in ((300.0, 300.0), (310.0, 300.0), (320.0, 300.0), (11.0, 11.0)):
        assert p in fp
        assert fph[fp.index(p)] == CP.G


def test_station_bit_sites_stay_fixed_with_ft_resite():
    fp, fph = fixed_points(True)
    assert (11.0, 11.0) not in fp                 # ft sites are re-sited after the search
    for p in ((300.0, 300.0), (310.0, 300.0), (320.0, 300.0)):
        assert p in fp and fph[fp.index(p)] == CP.G
