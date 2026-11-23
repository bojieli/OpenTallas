"""COORD flow review 11-22 item 2: static placement-geometry advisories (WARN only, never a gate)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as A  # noqa: E402
import plan_advisory as PA  # noqa: E402


def T(**kw):
    t = {"outline_um": [400.0, 400.0]}
    t.update(kw)
    return {"partition_types": {"t": t}}


def test_density_bksel_shape_and_clean():
    packed = [[100.0 + 1.404 * (i % 18), 100.0 + 0.27 * (i // 18)] for i in range(3670)]   # 3,670 sites in ~26 um
    out = A.density(T(internal_stations=[{"conn": "x", "regs_um": [[1, 1]], "bit_sites_um": [packed]}]), "p")
    assert len(out) == 1 and out[0].startswith("WARN ADV-STATION-DENSITY t:") and "internal_stations[0]" in out[0]
    spread = [[10.0 + 12 * (i % 30), 10.0 + 12 * (i // 30)] for i in range(600)]
    assert A.density(T(internal_stations=[{"bit_sites_um": [spread]}]), "p") == []


def test_site_on_row():
    ok, off = [4.32 + 0.054 * 100, 4.32 + 0.27 * 50], [4.32 + 0.054 * 100 + 0.02, 4.32 + 0.27 * 50]
    assert A.on_row(T(internal_stations=[{"bit_sites_um": [[ok]]}]), "p") == []
    out = A.on_row(T(internal_stations=[{"bit_sites_um": [[ok, off]]}]), "p")
    assert "1 exact site(s) off the row/site grid" in out[0]
    assert A.on_row(T(ft_slots=[{"bit_sites_um": [[off]]}]), "p") == []          # ft sites: gen snaps them


def test_place_region_firm_empty_and_bad_box():
    rs = {"u_ringctl.ctl_q0": [10, 10], "u_ringctl.ctl_q1": [12, 10]}
    out = A.region(T(relay_sites=rs, place_regions=[{"name": "ringctl_coll_i0", "inst_re": "^(u_ringctl\\.ctl_q0|u_ringctl\\.ctl_q1)$", "cone": "between"}]), "p")
    assert out and "0 movable cells" in out[0]
    assert A.region(T(relay_sites=rs, place_regions=[{"name": "a", "inst_re": "u_core/.*"}]), "p") == []
    out = A.region(T(place_regions=[{"name": "b", "inst_re": "x", "box_um": [10, 10, 10, 50]}, {"name": "c", "inst_re": "(", "centre_um": [999, 5]}]), "p")
    assert len(out) == 2 and "empty" in out[0] and "does not compile" in out[1] and "outside CORE_AREA" in out[1]


def test_bands():
    core = {"inst": "u_m", "origin_um": [100.0, 100.0], "outline_um": [50.0, 50.0]}
    band = {"rect_um": [90.0, 90.0, 160.0, 120.0], "padded_data_storage_flops": 5000}
    t = T(hard_cores=[core], clock={"landing_contract": {"bands": {"b0_i": band}}})
    assert "ADV-BAND-BLOCKAGE t: landing band b0_i" in A.band_blockage(t, "p")[0]
    assert "ADV-BAND-GAP t: landing band b0_i" in A.band_gap(t, "p")[0]
    own = T(hard_cores=[{"inst": "cl_b0_i", "origin_um": [90.0, 90.0], "outline_um": [70.0, 30.0]}],
            clock={"landing_contract": {"bands": {"b0_i": band}}})
    assert A.band_blockage(own, "p") == [] and A.band_gap(own, "p") == []      # a hard ring child band is a macro
    free = T(clock={"landing_contract": {"bands": {"b0_i": dict(band, padded_data_storage_flops=320)}}})
    assert A.band_blockage(free, "p") == [] and A.band_gap(free, "p") == []


def test_registered_and_never_raise():
    names = dict(PA.CHECKS)
    for n in ("STATION-DENSITY", "SITE-ON-ROW", "PLACE-REGION", "BAND-BLOCKAGE", "BAND-GAP"):
        assert n in names
    bad = {"partition_types": {"t": {"outline_um": [1, 1], "internal_stations": "x"}}}
    for _n, fn in A.ALL:
        assert all(x.startswith("WARN ADV-") for x in fn(bad, "p"))
