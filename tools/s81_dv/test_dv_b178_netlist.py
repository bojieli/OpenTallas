"""S81-PLAN-1 11-10: --bound-data reads the bind's own die top (die_b178.v); its transport must be self-consistent."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_layer_compile as C  # noqa: E402

NET = """module dv_die ();
  dsfd_dvland_276 ld_ab (.ck_f(x), .i(w_ab_dst), .ck(c), .rs(r), .k(3'd2), .o(w_ab_lnd));
  dsfd_dvrlyh_276_EW st_ab_0 (.i(w_ab_src), .o(r_ab_0), .ck(a), .ck_o(b), .rs(r));
  dsfd_dvrlyh_276_EW st_ab_1 (.i(r_ab_0), .o(w_ab_dst), .ck(b), .ck_o(c), .rs(r));
endmodule
"""


def test_self_consistent():
    r = C.check_transport_self(NET)
    assert r == dict(landings=1, stations=2, links_with_stations=1, transport_self_check='PASS')


def test_station_gap_fails():
    with pytest.raises(ValueError, match='gaps'):
        C.check_transport_self(NET.replace('st_ab_1 ', 'st_ab_2 '))


def test_non_literal_k_fails():
    with pytest.raises(ValueError, match='K not literal'):
        C.check_transport_self(NET.replace(".k(3'd2)", ".k(KPARAM)"))


def test_no_landing_fails():
    with pytest.raises(ValueError):
        C.check_transport_self('\n'.join(l for l in NET.splitlines() if 'ld_ab' not in l))


def test_netlist_sha_must_match(tmp_path):
    t = tmp_path / 'results/arch/s81_dv_1016/bind9'
    t.mkdir(parents=True)
    import gzip
    (t / 'die.v.gz').write_bytes(gzip.compress(NET.encode()))
    n = tmp_path / 'die_b178.v'
    n.write_text(NET)
    with pytest.raises(ValueError, match='is not the bind netlist'):
        C.Die(tmp_path, netlist=n, netlist_sha='0' * 64)
    with pytest.raises(ValueError, match='is not the bind netlist'):
        C.Die(tmp_path, netlist=n, netlist_sha=None)


def _rtl(tmp_path, forms):
    d = tmp_path / 'rtl'
    d.mkdir()
    for i, f in enumerate(forms):
        p = '' if f is None else f', .RING_LAND({f})'
        (d / f's{i}.sv').write_text(f'module s{i}; ot_s81sl_xrt1 #(.FACE_LAND(2){p}, .OLAT(1)) u_xr (.clk(c));\nendmodule\n')
    return d


def test_bound_xrt_form(tmp_path):
    import xr_timing as X
    assert X.bound_xrt_ring_land(_rtl(tmp_path, [2, 2])) == (2, 2)
    assert X.XRT_FORMS['d2a543e4fd9f25b13ccece85058652ecb9ccae366353738b6da20346e9c030a9'] == {2}


@pytest.mark.parametrize('forms', [[2, 1], [2, None], []])
def test_bound_xrt_form_fails_closed(tmp_path, forms):
    import xr_timing as X
    with pytest.raises(ValueError):
        X.bound_xrt_ring_land(_rtl(tmp_path, forms))
