"""QC-CB-GEN-1115 strap_sites.py: tile_id strap ports sited on the pin face of the tile they feed."""
import strap_sites as SS


def test_crosses_same_test_as_the_kit_check():
    tile = [(86.4, 69.1, 544.3, 1226.9)]
    assert SS.crosses((630.0, 1300.0), (86.5, 1970.0), [(86.4, 1304.6, 544.3, 2462.4)])      # port -> far W-face pin over t23
    assert not SS.crosses((630.0, 1300.0), (544.2, 700.0), [(86.4, 1304.6, 544.3, 2462.4)])  # near, off the tile
    assert not SS.crosses((100, 100), (200, 100), tile)                                       # short
    assert not SS.crosses((10, 640), (40, 640), tile)                                         # outside any macro


def test_placed_pin_uses_the_plan_orientation():
    core = dict(origin_um=[86.4, 1304.64], outline_um=[457.92, 1157.76], orient="MY", track_offset_um=[0.0, 0.012])
    x, y = SS._placed(core, dict(x=457.824, y=665.004))
    assert abs(x - (86.4 + 0.096)) < 1e-6 and abs(y - (1304.64 + 0.012 + 665.004)) < 1e-6      # E-face pin of an MY tile sits on its W face


def test_declared_interior_skips_tile_id_and_reads_other_pins():
    t = dict(count_straps=[dict(name="strap_u_t_2_3_tile_id", sites_um=[[1, 1]]), dict(name="strap_ca_pad", sites_um=[[5.0, 6.0]])],
             clock=dict(taps=[dict(xy=[7, 8])], landing_contract=dict(pins=[dict(xy_um=[9, 10])])))
    assert sorted(SS._declared_interior(t)) == [(5.0, 6.0), (7.0, 8.0), (9.0, 10.0)]
