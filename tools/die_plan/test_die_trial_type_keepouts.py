"""DIE-QC-47: --clock-type-keepouts makes a type's clock.keepouts_um a forbidden die clock-cell site (+2.16 um halo).
Default off keeps SiteMap byte-identical (KV plan_c already carries tile keep-outs that the die tree never read)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import die_trial as D  # noqa: E402


class _P:
    W, H = 400.0, 200.0
    die = {}
    types = {"phy": {"outline_um": [200.0, 200.0], "clock": {"keepouts_um": [[0.0, 0.0, 150.0, 190.0]]}},
             "soft": {"outline_um": [200.0, 200.0]}}
    parts = {"p0": {"type": "phy", "origin_um": [0.0, 0.0], "orient": "R0"},
             "p1": {"type": "phy", "origin_um": [200.0, 0.0], "orient": "MX"},
             "s": {"type": "soft", "origin_um": [0.0, 200.0], "orient": "R0"}}

    def to_die(self, n, q):
        p = self.parts[n]
        x, y = q
        if p["orient"] == "MX":
            y = self.types[p["type"]]["outline_um"][1] - y
        return p["origin_um"][0] + x, p["origin_um"][1] + y


def _site(flag):
    old = D.CLOCK_TYPE_KEEPOUTS
    try:
        D.CLOCK_TYPE_KEEPOUTS = flag
        return D.SiteMap(_P())
    finally:
        D.CLOCK_TYPE_KEEPOUTS = old


def test_default_off_ignores_type_keepouts():
    s = _site(False)
    assert s.forb == []
    assert s.legal((75.0, 95.0))


def test_opt_in_forbids_keepout_plus_halo_in_die_frame():
    s = _site(True)
    assert len(s.forb) == 2 and {r[4] for r in s.forb} == {"keepout"}
    assert s.why((75.0, 95.0)) == "keepout"           # inside the R0 body
    assert s.why((151.0, 95.0)) == "keepout"          # inside the 2.16 um halo
    assert s.legal((153.0, 95.0))                     # outside body + halo
    assert s.legal((75.0, 193.0))                     # free strip above the R0 body
    # MX instance: type y [0,190] -> die y [10,200]; the free strip is now at the bottom
    assert s.why((275.0, 100.0)) == "keepout"
    assert s.legal((275.0, 5.0))
    assert s.why((275.0, 8.5)) == "keepout"           # halo below the mirrored body


def test_ot_clk_argv_maps_top_type_keepouts():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clk"))
    import inspect
    import ot_clk
    src = inspect.getsource(ot_clk)
    assert 'top.get("type_keepouts")' in src and '"--clock-type-keepouts"' in src


def test_landing_band_rect_variants_exclude_clock_sites(monkeypatch):
    class Bands(_P):
        types = {'band': {'outline_um': [200., 200.], 'clock': {'landing_contract': {'bands': {
            'a': {'rect_um': [80., 60., 160., 110.]},
            'b': {'rects_um': [[20., 20., 40., 40.]]},
            'c': {'band_fixed_um': {'part': [20., 130., 40., 150.]}},
            'd': {'multi_rect_um': [[170., 20., 190., 40.]]}
        }}}}}
        parts = {'p0': {'type': 'band', 'origin_um': [0., 0.], 'orient': 'R0'},
                 'p1': {'type': 'band', 'origin_um': [200., 0.], 'orient': 'MX'}}
    monkeypatch.setattr(D, 'CLOCK_TYPE_KEEPOUTS', False)
    plain = D.SiteMap(Bands())
    assert plain.forb == [] and plain.legal((100., 90.))
    monkeypatch.setattr(D, 'CLOCK_TYPE_KEEPOUTS', True)
    site = D.SiteMap(Bands())
    assert len(site.forb) == 8 and all(r[4] == 'band' for r in site.forb)
    for q in [(100., 90.), (30., 30.), (30., 140.), (180., 30.), (300., 120.)]:
        assert site.why(q) == 'band'
    # The point is clear, but a native1.62um cell at it overlaps the band.
    assert site.legal((78.8, 90.))
    monkeypatch.setattr(D, 'CLOCK_BODY_SITES', True)
    monkeypatch.setattr(D, 'DME_ACTUAL_MAX_UM', None)
    assert D.clock_site(Bands()).why((78.8, 90.)) == 'band'
    assert D.clock_site(Bands()).legal((162., 90.))


def test_reserved_channel_flag_keeps_clock_bodies_out_of_seal_ring(monkeypatch):
    class Channel:
        W, H = 400., 200.
        types = {'t': {'outline_um': [200., 200.]}}
        parts = {'p': {'type': 't', 'origin_um': [0., 0.]}}

        def __init__(self, flag=None):
            ch = {'rect_um': [200., 0., 400., 200.]}
            if flag is not None:
                ch['clock_channel'] = flag
            self.die = {'channels': [ch]}

        def to_die(self, n, q):
            return q

    monkeypatch.setattr(D, 'CLOCK_TYPE_KEEPOUTS', False)
    assert D.SiteMap(Channel()).legal((300., 90.))  # existing default unchanged
    assert D.SiteMap(Channel(True)).legal((300., 90.))
    point = D.SiteMap(Channel(False))
    assert point.why((300., 90.)) == 'reserved_channel'
    assert point.legal((198.8, 90.))
    monkeypatch.setattr(D, 'CLOCK_BODY_SITES', True)
    monkeypatch.setattr(D, 'DME_ACTUAL_MAX_UM', None)
    assert D.clock_site(Channel(False)).why((198.8, 90.)) == 'reserved_channel'


def test_fixed_ft_envelopes_coalesce_and_keep_native_clock_bodies_clear(monkeypatch):
    class Fixed(_P):
        types = {'ft': {'outline_um': [200., 200.], 'ft_slots': [dict(
            name='ft0', width=2, stations=3, bit_site_cell_um=[1.404, .27],
            bit_sites_um=[[[80., 60.], [80., 60.27], [82., 60.]],
                          [[80., 60.54], [80., 60.81], [82., 60.27]]]) ]}}
        parts = {'p0': {'type': 'ft', 'origin_um': [0., 0.], 'orient': 'R0'},
                 'p1': {'type': 'ft', 'origin_um': [200., 0.], 'orient': 'MX'}}
    assert len(D.fixed_ft_rects(Fixed.types['ft'])) == 2
    monkeypatch.setattr(D, 'CLOCK_TYPE_KEEPOUTS', False)
    assert D.SiteMap(Fixed()).forb == []
    monkeypatch.setattr(D, 'CLOCK_TYPE_KEEPOUTS', True)
    point = D.SiteMap(Fixed())
    assert len(point.forb) == 4
    assert point.why((80.1, 60.1)) == 'ft_fixed'
    assert point.why((280.1, 139.2)) == 'ft_fixed'  # mirrored footprint
    assert point.legal((81.8, 60.1))
    monkeypatch.setattr(D, 'CLOCK_BODY_SITES', True)
    monkeypatch.setattr(D, 'DME_ACTUAL_MAX_UM', None)
    assert D.clock_site(Fixed()).why((81.8, 60.1)) == 'ft_fixed'
    assert D.clock_site(Fixed()).legal((84., 60.1))


def test_spatial_wall_components_preserve_touching_transitive_geometry():
    class Walls:
        b = 250.
        forb = [(-20., -5., 0., 5., 'a'), (0., 5., 10., 15., 'b'),
                (10., 14., 30., 16., 'c'), (62.5, 60., 70., 70., 'd'),
                (70., 70., 80., 80., 'e'), (200., 200., 210., 210., 'f')]
    rects, components = D._wall_components(Walls())
    got = {frozenset(ids): box for ids, box in components}
    assert rects == Walls.forb
    assert got == {frozenset([0, 1, 2]): (-20., -5., 30., 16.),
                   frozenset([3, 4]): (62.5, 60., 80., 80.),
                   frozenset([5]): (200., 200., 210., 210.)}


def test_point_keepouts_forbid_planned_register_points(monkeypatch):
    class Pts(_P):
        types = {'t': {'outline_um': [200., 200.],
                       'ft_slots': [dict(name='ft0', width=1, stations=2, bit_site_cell_um=[1.404, .27],
                                         bit_sites_um=[[[80., 60.], [80., 60.27]]], regs_um=[[0., 50.], [40., 50.]])],
                       'internal_stations': [dict(conn='bus:x', regs_um=[[120., 120.], [200., 120.]])],
                       'clock': {'landing_reader_start': {'branches': {'b': {'stages': [{'xy_um': [150., 30.]}]}}},
                                 'landing_writer_start': {'branches': {'o': {'stages': [{'xy_um': [20., 180.]}]}}}}}}
        parts = {'p0': {'type': 't', 'origin_um': [0., 0.], 'orient': 'R0'},
                 'p1': {'type': 't', 'origin_um': [200., 0.], 'orient': 'MX'}}
    monkeypatch.setattr(D, 'CLOCK_TYPE_KEEPOUTS', False)
    monkeypatch.setattr(D, 'CLOCK_POINT_KEEPOUT_UM', None)
    assert D.SiteMap(Pts()).forb == []                                   # default: unchanged
    rects = D.planned_point_rects(Pts.types['t'], 3.0)
    assert len(rects) == 5                                               # 1 FT column + 4 interior points (2 face points skipped)
    monkeypatch.setattr(D, 'CLOCK_POINT_KEEPOUT_UM', 3.0)
    site = D.SiteMap(Pts())
    assert len(site.forb) == 10
    for q in ((80.1, 60.1), (79.6, 60.1), (40., 50.), (42.9, 52.9), (120., 120.), (150., 30.), (20., 180.), (350., 170.)):
        assert site.why(q) == 'plan_point', q
    for q in ((78.9, 60.1), (0.9, 50.), (199., 120.), (43.5, 50.), (150., 34.)):
        assert site.legal(q), q
    near = site.nearest((150., 30.))
    assert site.legal(near) and abs(near[0] - 150.) + abs(near[1] - 30.) < 4.0


def test_ot_clk_argv_maps_top_point_keepouts():
    import importlib
    sys_path = str((__import__('pathlib').Path(__file__).resolve().parents[1] / 'clk'))
    __import__('sys').path.insert(0, sys_path)
    O = importlib.import_module('ot_clk')
    src = open(O.__file__).read()
    assert 'point_keepouts_um' in src and '--clock-point-keepouts' in src
