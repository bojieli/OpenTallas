"""QC-STRAP-TRACK 11-14 (TYPE-QCCOLLN): ID/count strap pin sites are written on their layer track grid.
sle_fw_v1 straps sat half an M5 pitch off track (x 302.4000 vs track 302.424/302.376): DRT-0206 route collapse."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402

M5 = {"dir": "V", "pitch_um": 0.048, "offset_um": 0.024}


def _plan(sites, layer="M5", layers=None):
    t = {"id_straps": [dict(name="strap_ca_k_rsn_i", width=len(sites), layer=layer, sites_um=sites)]}
    return SimpleNamespace(types={"t": t}, layers={"M5": M5} if layers is None else layers), "t"


def test_half_pitch_off_strap_sites_snap_to_the_m5_track():
    P, tn = _plan([[302.4, 939.4746], [315.36, 939.4746], [319.68, 892.2054]])
    for name, ln, x, y in G.strap_pin_sites(P, tn):
        k = (x - 0.024) / 0.048
        assert abs(k - round(k)) < 1e-6, (name, x)        # on a track
        assert abs(x - {"strap_ca_k_rsn_i[0]": 302.4, "strap_ca_k_rsn_i[1]": 315.36,
                        "strap_ca_k_rsn_i[2]": 319.68}[name]) <= 0.024 + 1e-9   # moved by at most half a pitch
    assert [s[3] for s in G.strap_pin_sites(P, tn)] == [939.4746, 939.4746, 892.2054]   # along-track coordinate kept


def test_on_track_strap_sites_keep_their_bytes():
    P, tn = _plan([[302.424, 10.0], [315.384, 11.5]])
    assert [(s[2], s[3]) for s in G.strap_pin_sites(P, tn)] == [(302.424, 10.0), (315.384, 11.5)]


def test_horizontal_layer_snaps_y_and_unknown_layer_is_unchanged():
    P, tn = _plan([[5.0, 10.02]], layer="M4", layers={"M4": {"dir": "H", "pitch_um": 0.048, "offset_um": 0.024}})
    (_, _, x, y), = G.strap_pin_sites(P, tn)
    assert x == 5.0 and abs((y - 0.024) / 0.048 - round((y - 0.024) / 0.048)) < 1e-6
    P, tn = _plan([[302.4, 9.0]], layers={})
    assert [(s[2], s[3]) for s in G.strap_pin_sites(P, tn)] == [(302.4, 9.0)]
